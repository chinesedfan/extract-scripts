#!/usr/bin/env python
import os
import sys
import unitypack
from argparse import ArgumentParser, FileType
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

	dbfxml = ElementTree.parse(dbf)
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


def merge_card_assets(cards):
	print("Performing card merge on %i items" % (len(cards)))

	def _clean_tag(tag):
		locale_elems = {e.tag: e for e in tag}
		keys = sorted(locale_elems.keys())
		for locale in IGNORE_LOCALES:
			if locale in keys:
				keys.pop(keys.index(locale))
		if "enUS" in keys:
			# When enUS was removed from TriggeredPowerHistoryInfo,
			# the other locales weren't...
			keys.insert(0, keys.pop(keys.index("enUS")))
		tag[:] = [locale_elems[k] for k in keys]
		tag.attrib["type"] = "LocString"
		# unescape newlines
		for t in tag:
			t.text = t.text.replace("\\n", "\n")

	for id, entity in cards.items():
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

	return make_carddefs(cards)


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


def merge_locale_assets(data):
	print("Performing locale merge")
	entities = {}

	# Ensure we process enUS first
	locales = sorted(data.keys())
	locales.insert(0, locales.pop(locales.index("enUS")))

	for locale in locales:
		xml = data[locale]
		for entity in xml.findall("Entity"):
			id = entity.attrib["CardID"]
			# print("Merging card %r" % (id))
			if id not in entities:
				_prepare_strings(entity, locale)
				entities[id] = entity
			else:
				_merge_strings(entities[id], entity, locale)

	return make_carddefs(entities)


def detect_build(path):
	return int([x for x in path.split(os.path.sep) if x.isdigit()][0])


def main():
	p = ArgumentParser()
	p.add_argument("bundles", nargs="?", type=FileType("rb"))
	p.add_argument("-o", "--outfile", nargs=1, type=FileType("w"))
	p.add_argument("--dbf", nargs="?", type=FileType("r"))
	args = p.parse_args(sys.argv[1:])

	bundle = args.bundles
	build = detect_build(bundle.name)
	bundle = unitypack.load(bundle)
	data = {}
	for asset in bundle.assets:
		if asset.name == "CAB-cardxml0":
			do_locales = len(asset.objects) < 20
			print("Processing %r" % (asset))
			for id, obj in asset.objects.items():
				d = obj.read()
				if obj.type == "TextAsset":
					if do_locales and d.name in IGNORE_LOCALES:
						continue
					data[d.name] = ElementTree.fromstring(d.script)

			if do_locales:
				xml = merge_locale_assets(data)
			else:
				xml = merge_card_assets(data)
			break

	if args.dbf:
		print("Processing DBF %r" % (args.dbf.name))
		clean_entourage_ids(xml, args.dbf)

	xml.attrib["build"] = str(build)

	print("Writing to %r" % (args.outfile[0].name))
	args.outfile[0].write(pretty_xml(xml))


if __name__ == "__main__":
	main()
