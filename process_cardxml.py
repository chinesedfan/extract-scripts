#!/usr/bin/env python
import os
import re
import sys
import unitypack
from argparse import ArgumentParser, FileType
from xml.dom import minidom
from lxml import etree as ElementTree
from hearthstone import cardxml
from hearthstone.dbf import Dbf
from hearthstone.enums import GameTag


MISSING_HERO_POWERS = {
	"BRM_027h": 2319,  # "BRM_027p"
	"EX1_323h": 1178,  # "EX1_tk33"
}

IGNORE_LOCALES = ("enGB", "ptPT")

SPARE_PART_RE = re.compile(r"PART_\d+")


def pretty_xml(xml):
	ret = ElementTree.tostring(xml, encoding="utf-8")
	ret = minidom.parseString(ret).toprettyxml(indent="\t", encoding="utf-8")
	return b"\n".join(line for line in ret.split(b"\n") if line.strip())


def string_to_bool(s):
	if s == "False":
		return False
	if s == "True":
		return True
	raise ValueError(s)


def detect_build(path):
	path_fragments = [x for x in path.split(os.path.sep) if x.isdigit()]
	if not path_fragments:
		return
	return int(path_fragments[0])


def guess_overload(text):
	sre = re.search(r"Overload[^(]+\((\d+)\)", text)
	if sre is None:
		return 0
	return int(sre.groups()[0])


def guess_spellpower(text):
	sre = re.search(r"Spell (?:Power|Damage)(?:</b>)? \+(\d+)", text)
	if sre is None:
		return 0
	return int(sre.groups()[0])


class CardXMLProcessor:
	unity3d_filenames = [
		"cards.unity3d",
		"cards0.unity3d",
		"cards1.unity3d",
		"cards2.unity3d",
		"cardxml0.unity3d",
	]

	tag_dbf_localized_columns = [
		(GameTag.CARDNAME, "NAME"),
		(GameTag.CARDTEXT_INHAND, "TEXT_IN_HAND"),
		(GameTag.FLAVORTEXT, "FLAVOR_TEXT"),
		(GameTag.HOW_TO_EARN, "HOW_TO_GET_CARD"),
		(GameTag.HOW_TO_EARN_GOLDEN, "HOW_TO_GET_GOLD_CARD"),
		(GameTag.TARGETING_ARROW_TEXT, "TARGET_ARROW_TEXT"),
	]

	def __init__(self):
		self._p = ArgumentParser()
		self._p.add_argument("files", nargs="+", type=FileType("rb"))
		self._p.add_argument("-o", "--outfile", nargs="?", type=FileType("wb"))
		self._p.add_argument("--dbf-dir", nargs="?", type=str)
		self._p.add_argument("--build", type=int, default=None)
		self._p.add_argument("--raw", action="store_true")

		# The final dict of entities
		self.entities = {}

		# Reverse lookups dbf_id -> cardid
		self.dbf_ids = {}

		# Reverse lookups guid -> cardid
		self.guids = {}

		# Hero power dict
		self.hero_powers = {}

		# Localized strings
		self.entity_strings = {}

	def info(self, msg):
		sys.stderr.write("[INFO] %s\n" % (msg))

	def warn(self, msg):
		sys.stderr.write("[WARN] %s\n" % (msg))

	def error(self, msg):
		sys.stderr.write("[ERROR] %s\n" % (msg))
		exit(1)

	def parse_bundle(self, f):
		if os.path.basename(f.name) not in self.unity3d_filenames:
			# Only parse files that have a whitelisted name
			f.close()
			return

		bundle = unitypack.load(f)
		asset = bundle.assets[0]
		self.info("Processing %r" % (asset))

		for obj in asset.objects.values():
			if obj.type == "TextAsset":
				d = obj.read()
				if d.name in IGNORE_LOCALES:
					continue
				if d.script.startswith("<CardDefs>"):
					xml = ElementTree.fromstring(d.script)
					self.parse_full_carddefs(xml, d.name)
				elif d.script.startswith("<?xml "):
					xml = ElementTree.fromstring(d.script.encode("utf-8"))
					self.parse_single_entity_xml(xml, d.name, locale=None)
				else:
					self.error("Bad TextAsset: %r" % (d))

	def parse_single_entity_xml(self, xml, id, locale=None):
		"""
		Parse a single Entity tag
		If the locale argument is set, read it as single-locale.
		Otherwise, read it as merged-locales.
		"""
		entity = cardxml.CardXML(id)
		entity.version = int(xml.attrib["version"])
		self.entity_strings[id] = {k: {} for k in entity.strings}

		for e in xml:
			if e.tag == "Tag":
				tag = GameTag(int(e.attrib["enumID"]))
				if e.attrib["type"] == "String":
					if locale:
						self.entity_strings[id][tag][locale] = e.text
					else:
						for loc in e:
							self.entity_strings[id][tag][loc.tag] = loc.text
				else:
					value = int(e.attrib["value"])
					entity.tags[tag] = value
			elif e.tag == "ReferencedTag":
				tag = GameTag(int(e.attrib["enumID"]))
				value = int(e.attrib["value"])
				entity.referenced_tags[tag] = value
			elif e.tag == "MasterPower":
				entity.master_power = e.text.strip()
			elif e.tag == "Power":
				power = cardxml._read_power_tag(e)
				entity.powers.append(power)
			elif e.tag == "EntourageCard":
				card_id = e.attrib.pop("cardID")
				if not card_id:
					raise ValueError("Missing cardID on EntourageCard for entity %r" % (entity))
				entity.entourage.append(card_id)
				if e.attrib:
					raise NotImplementedError("EntourageCard attributes: %r" % (e.attrib))
			elif e.tag == "TriggeredPowerHistoryInfo":
				effect_index = e.attrib.pop("effectIndex")
				show_in_history = string_to_bool(e.attrib.pop("showInHistory"))
				entity.triggered_power_history_info.append({
					"effectIndex": effect_index,
					"showInHistory": show_in_history,
				})
				if e.attrib:
					raise NotImplementedError("TriggeredPowerHistoryInfo attributes: %r" % (e.attrib))
			else:
				raise NotImplementedError("Unhandled tag: %r" % (e.tag))

		self.entities[id] = entity

	def parse_raw(self, f):
		name = os.path.splitext(os.path.basename(f.name))[0]
		xml = ElementTree.fromstring(f.read())
		self.parse_full_carddefs(xml, name)

	def parse_full_carddefs(self, xml, locale):
		self.info("Reading full CardDefs file %r" % (locale))

		for entity_xml in xml.findall("Entity"):
			id = entity_xml.attrib["CardID"]
			if id not in self.entities:
				self.parse_single_entity_xml(entity_xml, id, locale)

			# Parse the entity's strings into self.entity_strings
			for e in entity_xml.findall("Tag[@type='String']"):
				tag = GameTag(int(e.attrib["enumID"]))
				self.entity_strings[id][tag][locale] = e.text

	def parse_card_dbf(self, path):
		self.info("Processing CARD DBF %r" % (path))
		dbf = Dbf.load(path)

		# Whether we'll set the CARD_TAG dbf-style (post-15590) string tags
		apply_locstrings = "NAME" in dbf.columns

		for record in dbf.records:
			id = record["ID"]
			card_id = record["NOTE_MINI_GUID"]
			self.dbf_ids[id] = card_id

			long_guid = record.get("LONG_GUID")
			if long_guid:
				self.guids[long_guid] = card_id

			if apply_locstrings:
				self.entity_strings[card_id] = {}
				for tag, column in self.tag_dbf_localized_columns:
					r = record.get(column) or {}
					self.entity_strings[card_id][tag] = r

				# Artist name is not localized in the new layout
				artist = record.get("ARTIST_NAME") or ""
				self.entity_strings[card_id][GameTag.ARTISTNAME] = {"enUS": artist}

			if card_id not in self.entities:
				self.warn("Entity %r not found in card defs but present in CARD.xml" % (card_id))
				continue

			entity = self.entities[card_id]
			entity.dbf_id = id

			hero_power_id = record.get("HERO_POWER_ID")
			if hero_power_id:
				entity.tags[GameTag.HERO_POWER] = hero_power_id

	def parse_card_tag_dbf(self, path):
		self.info("Processing CARD_TAG DBF %r" % (path))
		dbf = Dbf.load(path)

		for record in dbf.records:
			dbf_id = record["CARD_ID"]
			card_id = self.dbf_ids[dbf_id]
			tag = record["TAG_ID"]
			value = record["TAG_VALUE"]
			is_reference = record["IS_REFERENCE_TAG"]
			# ispower = record["IS_POWER_KEYWORD_TAG"]
			if card_id not in self.entities:
				self.warn("Entity %r not found in card defs but present in CARD_TAG.xml" % (card_id))
			elif is_reference:
				self.entities[card_id].referenced_tags[tag] = value
			else:
				self.entities[card_id].tags[tag] = value

	def generate_xml(self):
		self.info("Processing %i entities" % (len(self.entities)))
		root = ElementTree.Element("CardDefs", build=str(self.build))
		ids = sorted(self.entities.keys(), key=str.lower)
		for id in ids:
			root.append(self.entities[id].to_xml())

		return pretty_xml(root)

	def clean_entity(self, entity):
		# Update entity strings from self.entity_strings
		if entity.id in self.entity_strings:
			for tag in cardxml.STRING_TAGS:
				s = self.entity_strings[entity.id].pop(tag, {})
				if "enUS" in s:
					entity.strings[tag] = s["enUS"].replace("\\n", "\n").strip()

			for tag, strings in self.entity_strings[entity.id].items():
				for locale, text in strings.items():
					if locale in IGNORE_LOCALES:
						continue

					if self.build < 3640 and locale != "enUS":
						# Nothing was localized before that build
						if text == self.entity_strings[entity.id][tag]["enUS"]:
							continue

					text = text.replace("\\n", "\n").strip()
					if text:
						entity.strings[tag][locale] = text

		description = entity.description

		# Parse the exact overload amount
		if entity.overload:
			assert entity.overload == 1
			overload = guess_overload(description)
			if not overload:
				self.warn("Could not guess overload for %r: %r" % (entity, description))
			else:
				entity.tags[GameTag.OVERLOAD] = overload

		# Parse the exact spellpower amount
		if entity.spell_damage:
			assert entity.spell_damage == 1
			sp = guess_spellpower(description)
			if not sp:
				self.warn("Could not guess spell power for %r: %r" % (entity, description))
			else:
				entity.tags[GameTag.SPELLPOWER] = sp

		# Set the "shrouded" tags if available
		if self.build < 6024:
			SHROUDED = "Can't be targeted by Spells or Hero Powers."
		else:
			SHROUDED = "Can't be targeted by spells or Hero Powers."
		if SHROUDED in description:
			entity.tags[GameTag.CANT_BE_TARGETED_BY_SPELLS] = True
			entity.tags[GameTag.CANT_BE_TARGETED_BY_HERO_POWERS] = True

		# Set the CANT_ATTACK tag if available
		if "Can't attack." in description or "Can't Attack." in description:
			entity.tags[GameTag.CANT_ATTACK] = True

		# Mark all spare parts with the SPARE_PART tag
		if SPARE_PART_RE.match(entity.id):
			entity.tags[GameTag.SPARE_PART] = True

		if entity.id in MISSING_HERO_POWERS:
			assert not entity.tags.get(GameTag.HERO_POWER, 0)
			entity.tags[GameTag.HERO_POWER] = MISSING_HERO_POWERS[entity.id]

		# Set the hero power cardIDs
		hero_power = entity.tags.get(GameTag.HERO_POWER, 0)
		if hero_power:
			if hero_power not in self.dbf_ids:
				self.warn("Hero Power %r for %r not found" % (hero_power, entity))
			else:
				entity.hero_power = self.dbf_ids[hero_power]

		# Clean the entourage guids into mini guids
		for i, entourage in enumerate(entity.entourage):
			if len(entourage) >= 34:
				entity.entourage[i] = self.guids[entourage]

	def run(self, args):
		self.args = self._p.parse_args(args)

		self.build = self.args.build or detect_build(self.args.files[0].name)
		if self.build is None:
			self.error("Could not detect build. Use --build.")

		for f in self.args.files:
			if self.args.raw:
				self.parse_raw(f)
			else:
				self.parse_bundle(f)

		if self.args.dbf_dir:
			path = os.path.join(self.args.dbf_dir, "CARD.xml")
			if os.path.exists(path):
				self.parse_card_dbf(path)

			# Check for CARD_TAG.xml too
			path = os.path.join(self.args.dbf_dir, "CARD_TAG.xml")
			if os.path.exists(path):
				self.parse_card_tag_dbf(path)

		for entity in self.entities.values():
			self.clean_entity(entity)

		xml = self.generate_xml()

		if self.args.outfile:
			self.info("Writing to %r" % (self.args.outfile.name))
			self.args.outfile.write(xml)
		else:
			sys.stdout.write(xml.decode("utf-8"))


def main():
	app = CardXMLProcessor()
	app.run(sys.argv[1:])


if __name__ == "__main__":
	main()
