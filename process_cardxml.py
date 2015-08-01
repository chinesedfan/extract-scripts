#!/usr/bin/env python
import os
import sys
from xml.dom import minidom
from xml.etree import ElementTree


UNTRANSLATED_ENUMIDS = (
	"342",  # ArtistName
)


def pretty_xml(xml):
	ret = ElementTree.tostring(xml)
	ret = minidom.parseString(ret).toprettyxml(indent="\t")
	return "\n".join(line for line in ret.split("\n") if line.strip())


def clean_entity(xml):
	# Reorder entities and ensure they have names
	# for tag in xml.findall("Tag"):
	# 	pass

	return xml


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
				locale_elems = {e.tag: e for e in tag}
				keys = sorted(locale_elems.keys())
				# Sort enUS at the beginning
				keys.insert(0, keys.pop(keys.index("enUS")))
				tag[:] = [locale_elems[k] for k in keys]
				tag.attrib["type"] = "LocString"
				# unescape newlines
				for t in tag:
					t.text = t.text.replace("\\n", "\n")

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
		if locale == "enGB":
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
		print("Usage: %s [indir] [outfile]" % sys.argv[0])
		exit(1)

	indir = sys.argv[1]
	outfile = sys.argv[2]

	if not os.path.exists(os.path.join(indir, "enUS.txt")):
		xml = merge_card_files(indir)
	else:
		xml = merge_locale_files(indir)

	with open(outfile, "w") as f:
		f.write(pretty_xml(xml))


if __name__ == "__main__":
	main()
