#!/usr/bin/env python
import os
import re
import sys
import unitypack
from argparse import ArgumentParser, FileType
from xml.dom import minidom
from xml.etree import ElementTree
from hearthstone.dbf import Dbf
from hearthstone.enums import GameTag


MISSING_HERO_POWERS = {
	"BRM_027h": "BRM_027p",
	"EX1_323h": "EX1_tk33",
}

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


def print_info(*args):
	print("[INFO]", *args, file=sys.stderr)


def print_warn(*args):
	print("[WARN]", *args, file=sys.stderr)


def pretty_xml(xml):
	ret = ElementTree.tostring(xml, encoding="utf-8")
	ret = minidom.parseString(ret).toprettyxml(indent="\t", encoding="utf-8")
	return b"\n".join(line for line in ret.split(b"\n") if line.strip())


def clean_entity(xml):
	# Reorder entities and ensure they have names

	for tag in xml.findall("Tag"):
		enumid = int(tag.attrib["enumID"])
		if enumid in TAGS:
			name, type = TAGS[enumid]
			tag.attrib["name"] = name
			tag.attrib["type"] = type

	return xml


def set_tag(entity, tag, value, type):
	e = ElementTree.Element("Tag")
	e.attrib["enumID"] = str(int(tag))
	e.attrib["value"] = str(value)
	e.attrib["type"] = type
	entity.append(e)


def process_dbf(dbf, xml):
	print_info("Processing DBF %r" % (dbf))
	dbf = Dbf.load(dbf)

	db = {}
	guids = {}
	hero_powers = {}

	for record in dbf.records:
		id = record["ID"]
		mini_guid = record["NOTE_MINI_GUID"]
		db[id] = mini_guid

		long_guid = record.get("LONG_GUID")
		if long_guid:
			guids[long_guid] = mini_guid

		hero_power_id = record["HERO_POWER_ID"]
		if hero_power_id:
			hero_powers[mini_guid] = hero_power_id

	clean_entourage_ids(xml, guids)

	# Replace numeric id by card id
	for k, v in hero_powers.items():
		hero_powers[k] = db[v]

	# Some hero powers are missing from the DBF...
	for k, v in MISSING_HERO_POWERS.items():
		assert k not in hero_powers
		hero_powers[k] = v

	return hero_powers


def clean_entourage_ids(xml, guids):
	for entity in xml.findall("Entity"):
		for entourage in entity.findall("EntourageCard"):
			guid = entourage.attrib["cardID"]
			if len(guid) < 34:
				# Ignore mini-guids
				continue
			entourage.attrib["cardID"] = guids[guid]


def make_carddefs(entities):
	print_info("Processing %i entities" % (len(entities)))
	root = ElementTree.Element("CardDefs")
	ids = sorted(entities.keys(), key=lambda i: i.lower())
	for id in ids:
		entity = clean_entity(entities[id])
		root.append(entity)

	return root


def merge_card_assets(cards, build):
	print_info("Performing card merge on %i items" % (len(cards)))

	def _clean_tag(tag):
		locale_elems = {e.tag: e for e in tag}
		keys = sorted(locale_elems.keys())
		for locale in IGNORE_LOCALES:
			if locale in keys:
				keys.pop(keys.index(locale))

		# Nothing was localized before build 3604
		if build < 3604:
			keys = ["enUS"]

		elif "enUS" in keys:
			# When enUS was removed from TriggeredPowerHistoryInfo,
			# the other locales weren't...
			keys.insert(0, keys.pop(keys.index("enUS")))

		# Nothing was localized before build 3604
		tag[:] = [locale_elems[k] for k in keys]
		tag.attrib["type"] = "LocString"
		# unescape newlines
		for t in tag:
			t.text = t.text.replace("\\n", "\n")

	for id, entity in cards.items():
		# Fix the locale tags
		for tag in entity.findall("Tag[@type='String']"):
			if int(tag.attrib["enumID"]) == GameTag.ARTISTNAME:
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
		if int(tag.attrib["enumID"]) == GameTag.ARTISTNAME:
			continue
		newtag = _make_locale_tag(tag.text, locale)
		tag.text = ""
		tag.append(newtag)
		tag.attrib["type"] = "LocString"


def merge_locale_assets(data):
	print_info("Performing locale merge")
	entities = {}

	# Ensure we process enUS first
	locales = sorted(data.keys())
	locales.insert(0, locales.pop(locales.index("enUS")))

	for locale in locales:
		xml = data[locale]
		for entity in xml.findall("Entity"):
			id = entity.attrib["CardID"]
			# print_info("Merging card %r" % (id))
			if id not in entities:
				_prepare_strings(entity, locale)
				entities[id] = entity
			else:
				_merge_strings(entities[id], entity, locale)

	return make_carddefs(entities)


def detect_build(path):
	return int([x for x in path.split(os.path.sep) if x.isdigit()][0])


def guess_overload(text):
	sre = re.search(r"Overload[^(]+\((\d+)\)", text)
	if sre is None:
		print_warn("Could not guess overload in %r" % (text))
		return 0
	return int(sre.groups()[0])


def guess_spellpower(text):
	sre = re.search(r"Spell (?:Power|Damage)(?:</b>)? \+(\d+)", text)
	if sre is None:
		print_warn("Could not guess spell power in %r" % (text))
		return 0
	return int(sre.groups()[0])


def reverse_texture_path(path):
	return os.path.splitext(os.path.basename(path))[0]


def parse_bundles(files):
	carddefs, entities, textures = {}, {}, {}
	whitelist = [
		"cards.unity3d",
		"cards0.unity3d",
		"cards1.unity3d",
		"cards2.unity3d",
		"cardxml0.unity3d",
	]

	for f in files:
		if os.path.basename(f.name) not in whitelist:
			f.close()
			continue
		bundle = unitypack.load(f)
		asset = bundle.assets[0]
		print_info("Processing %r" % (asset))
		for obj in asset.objects.values():
			if obj.type == "TextAsset":
				d = obj.read()
				if d.name in IGNORE_LOCALES:
					continue
				if d.script.startswith("<CardDefs>"):
					carddefs[d.name] = ElementTree.fromstring(d.script)
				elif d.script.startswith("<?xml "):
					entities[d.name] = ElementTree.fromstring(d.script)
				else:
					raise Exception("Bad TextAsset %r" % (d))
			elif obj.type in ("CardDef", "MonoScript"):
				d = obj.read()
				if "m_GameObject" not in d:
					# We check for MonoScript because type checks through asset
					# references does not return the real class name yet.
					# This means we have to check for GameObject in the obj to
					# make sure it's actually a card.
					continue
				if d["m_GameObject"] is None:
					print_warn("Missing m_GameObject for %r" % (obj))
					continue
				cardid = d["m_GameObject"].resolve().name
				if "m_PortraitTexture" in d:
					ptr = d["m_PortraitTexture"]
					if not ptr:
						continue
					try:
						texture = ptr.resolve().name
					except NotImplementedError:
						texture = ""
				else:
					texture = reverse_texture_path(d.get("m_PortraitTexturePath", ""))
				if texture:
					textures[cardid] = texture

	return carddefs, entities, textures


def main():
	p = ArgumentParser()
	p.add_argument("files", nargs="+", type=FileType("rb"))
	p.add_argument("-o", "--outfile", nargs="?", type=FileType("wb"))
	p.add_argument("--dbf", nargs="?", type=str)
	p.add_argument("--build", type=int, default=None)
	p.add_argument("--raw", action="store_true")
	args = p.parse_args(sys.argv[1:])

	build = args.build or detect_build(args.files[0].name)

	if args.raw:
		carddefs = {}
		for f in args.files:
			name = os.path.splitext(os.path.basename(f.name))[0]
			carddefs[name] = ElementTree.fromstring(f.read())
			entities, textures = {}, {}
	else:
		carddefs, entities, textures = parse_bundles(args.files)

	if carddefs:
		xml = merge_locale_assets(carddefs)
	else:
		xml = merge_card_assets(entities, build)

	if args.dbf:
		hero_powers = process_dbf(args.dbf, xml)
	else:
		hero_powers = {}

	if build < 6024:
		SHROUDED = "Can't be targeted by Spells or Hero Powers."
	else:
		SHROUDED = "Can't be targeted by spells or Hero Powers."

	SPARE_PART_RE = re.compile(r"PART_\d+")

	for entity in xml.findall("Entity"):
		id = entity.attrib["CardID"]
		description = entity.find("Tag[@enumID='184']/enUS")
		description = description.text if description is not None else ""

		# Clean up MasterPower whitespace
		power = entity.find("MasterPower")
		if power is not None:
			power.text = power.text.strip()
			if not power.text:
				entity.remove(power)

		overload = entity.find("Tag[@enumID='215']")
		if overload is not None:
			overload.attrib["value"] = str(guess_overload(description))

		spellpower = entity.find("Tag[@enumID='192']")
		if spellpower is not None:
			spellpower.attrib["value"] = str(guess_spellpower(description))
			spellpower.attrib["type"] = "Int"

		if SHROUDED in description:
			set_tag(entity, GameTag.CANT_BE_TARGETED_BY_SPELLS, 1, type="Bool")
			set_tag(entity, GameTag.CANT_BE_TARGETED_BY_HERO_POWERS, 1, type="Bool")

		if "Can't attack." in description or "Can't Attack." in description:
			set_tag(entity, GameTag.CANT_ATTACK, 1, type="Bool")

		if SPARE_PART_RE.match(id):
			set_tag(entity, GameTag.SPARE_PART, 1, type="Bool")

		if id in textures:
			e = ElementTree.Element("Texture")
			e.text = textures[id]
			entity.append(e)

		if id in hero_powers:
			e = ElementTree.Element("HeroPower")
			e.attrib["cardID"] = hero_powers[id]
			entity.append(e)

	xml.attrib["build"] = str(build)

	if args.outfile:
		print_info("Writing to %r" % (args.outfile.name))
		args.outfile.write(pretty_xml(xml))
	else:
		print(pretty_xml(xml).decode("utf-8"))


if __name__ == "__main__":
	main()
