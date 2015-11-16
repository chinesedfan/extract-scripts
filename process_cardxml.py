#!/usr/bin/env python
import os
import sys
from xml.dom import minidom
from xml.etree import ElementTree


UNTRANSLATED_ENUMIDS = (
	"342",  # ArtistName
)

IGNORE_LOCALES = ("enGB", "ptPT")

TAGS = {
	32: ("TriggerVisual", "Bool"),
	45: ("Health", "Int"),
	47: ("Atk", "Int"),
	48: ("Cost", "Int"),
	114: ("Elite", "Bool"),
	183: ("CardSet", "CardSet"),
	184: ("CardTextInHand", "LocString"),
	185: ("CardName", "LocString"),
	187: ("Durability", "Int"),
	189: ("Windfury", "Bool"),
	190: ("Taunt", "Bool"),
	191: ("Stealth", "Bool"),
	192: ("Spellpower", "Bool"),
	194: ("Divine Shield", "Bool"),
	197: ("Charge", "Bool"),
	199: ("Class", "Class"),
	200: ("Race", "Race"),
	201: ("Faction", "Faction"),
	203: ("Rarity", "Rarity"),
	202: ("CardType", "CardType"),
	208: ("Freeze", "Bool"),
	212: ("Enrage", "Bool"),
	215: ("Recall", "Int"),
	217: ("Deathrattle", "Bool"),
	218: ("Battlecry", "Bool"),
	219: ("Secret", "Bool"),
	220: ("Combo", "Bool"),
	240: ("Cant Be Damaged", "Bool"),
	251: ("AttackVisualType", "AttackVisualType"),
	252: ("CardTextInPlay", "LocString"),
	268: ("DevState", "DevState"),
	293: ("Morph", "Bool"),
	321: ("Collectible", "Bool"),
	325: ("TargetingArrowText", "LocString"),
	330: ("EnchantmentBirthVisual", "EnchantmentVisualType"),
	331: ("EnchantmentIdleVisual", "EnchantmentVisualType"),
	335: ("InvisibleDeathrattle", "Bool"),
	338: ("OneTurnEffect", "Bool"),
	339: ("Silence", "Bool"),
	340: ("Counter", "Bool"),
	342: ("ArtistName", "String"),
	349: ("ImmuneToSpellpower", "Bool"),
	350: ("AdjacentBuff", "Bool"),
	351: ("FlavorText", "LocString"),
	361: ("HealTarget", "Bool"),
	362: ("Aura", "Bool"),
	363: ("Poisonous", "Bool"),
	364: ("HowToGetThisCard", "LocString"),
	365: ("HowToGetThisGoldCard", "LocString"),
	367: ("AIMustPlay", "Bool"),
	370: ("AffectedBySpellPower", "Bool"),
	388: ("SparePart", "Bool"),
}


def pretty_xml(xml):
	ret = ElementTree.tostring(xml)
	ret = minidom.parseString(ret).toprettyxml(indent="\t")
	return "\n".join(line for line in ret.split("\n") if line.strip())


def clean_entity(xml):
	# Reorder entities and ensure they have names

	for tag in xml.findall("Tag"):
		enumid = int(tag.attrib["enumID"])
		if enumid in TAGS:
			name, type = TAGS[enumid]
			tag.attrib["name"] = name
			tag.attrib["type"] = type

	return xml


def clean_entourage_ids(xml, dbf):
	guids = {}

	with open(dbf, "r") as f:
		dbfxml = ElementTree.parse(f)
		for record in dbfxml.findall("Record"):
			long_guid = record.find("./Field[@column='LONG_GUID']")
			if long_guid is None:
				return
			long_guid = long_guid.text
			mini_guid = record.find("./Field[@column='NOTE_MINI_GUID']").text
			guids[long_guid] = mini_guid

	for entity in xml.findall("Entity"):
		for entourage in entity.findall("EntourageCard"):
			guid = entourage.attrib["cardID"]
			if len(guid) < 34:
				# Ignore mini-guids
				continue
			entourage.attrib["cardID"] = guids[guid]


def make_carddefs(entities):
	root = ElementTree.Element("CardDefs")
	ids = sorted(entities.keys(), key=lambda i: i.lower())
	for id in ids:
		entity = clean_entity(entities[id])
		root.append(entity)

	return root


def merge_card_files(path):
	print("Performing card merge on %r" % (path))
	entities = {}

	def _clean_tag(tag):
		locale_elems = {e.tag: e for e in tag}
		keys = sorted(locale_elems.keys())
		for locale in IGNORE_LOCALES:
			if locale in keys:
				keys.pop(keys.index(locale))
		# Sort enUS at the beginning
		keys.insert(0, keys.pop(keys.index("enUS")))
		tag[:] = [locale_elems[k] for k in keys]
		tag.attrib["type"] = "LocString"
		# unescape newlines
		for t in tag:
			t.text = t.text.replace("\\n", "\n")

	for filename in os.listdir(path):
		with open(os.path.join(path, filename), "r") as f:
			xml = ElementTree.parse(f)
			entity = xml.getroot()
			id = entity.attrib["CardID"]
			entities[id] = entity

			# Fix the locale tags
			for tag in entity.findall("Tag[@type='String']"):
				if tag.attrib["enumID"] in UNTRANSLATED_ENUMIDS:
					# "untranslate" the string
					tag.text = tag.find("enUS").text
					for lt in tag:
						tag.remove(lt)
					continue
				_clean_tag(tag)

			# Very old TriggeredPowerHistoryInfo tags were sometimes localized
			tag = entity.find("TriggeredPowerHistoryInfo")
			if tag is not None and len(tag):
				_clean_tag(tag)

	return make_carddefs(entities)


def _make_locale_tag(text, locale):
	newtag = ElementTree.Element(locale)
	newtag.text = text
	return newtag


def _merge_strings(base, extra, locale):
	for tag in base.findall("Tag[@type='LocString']"):
		localetag = extra.find("Tag[@enumID='%s']" % (tag.attrib["enumID"]))
		text = localetag.text.strip()
		if text:
			tag.append(_make_locale_tag(localetag.text, locale))
	return base


def _prepare_strings(xml, locale):
	for tag in xml.findall("Tag[@type='String']"):
		if tag.attrib["enumID"] in UNTRANSLATED_ENUMIDS:
			continue
		newtag = _make_locale_tag(tag.text, locale)
		tag.text = ""
		tag.append(newtag)
		tag.attrib["type"] = "LocString"


def merge_locale_files(path):
	print("Performing locale merge on %r" % (path))
	entities = {}

	# Ensure we process enUS first
	files = sorted(os.listdir(path))
	files.insert(0, files.pop(files.index("enUS.txt")))

	for filename in files:
		locale = os.path.splitext(filename)[0]
		if locale in IGNORE_LOCALES:
			continue
		with open(os.path.join(path, filename), "r") as f:
			xml = ElementTree.parse(f)
			for entity in xml.findall("Entity"):
				id = entity.attrib["CardID"]
				# print("Merging card %r" % (id))
				if id not in entities:
					_prepare_strings(entity, locale)
					entities[id] = entity
				else:
					_merge_strings(entities[id], entity, locale)

	return make_carddefs(entities)


def main():
	if len(sys.argv) < 3:
		print("Usage: %s <indir> <outfile> [carddbf]" % sys.argv[0])
		exit(1)

	indir = sys.argv[1]
	outfile = sys.argv[2]

	if not os.path.exists(os.path.join(indir, "enUS.txt")):
		xml = merge_card_files(indir)
	else:
		xml = merge_locale_files(indir)

	if len(sys.argv) == 4:
		clean_entourage_ids(xml, sys.argv[3])

	with open(outfile, "w") as f:
		f.write(pretty_xml(xml))


if __name__ == "__main__":
	main()
