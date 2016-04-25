#!/usr/bin/env python
import sys
from argparse import ArgumentParser, FileType
from hearthstone.cardxml import load as load_cardxml


def card_diff(first, other):
	ret = {
		"entourage": (),
		"hero_power": (),
		"play_requirements": {},
		"tags": {},
	}

	for tag, value in other.tags.items():
		old_value = first.tags.get(tag, None)
		if value != old_value:
			ret["tags"][tag] = (old_value, value)

	for pr, value in other.requirements.items():
		old_value = first.requirements.get(pr, None)
		if value != old_value:
			ret["play_requirements"][pr] = (old_value, value)

	# Deleted tags
	for tag, old_value in first.tags.items():
		if tag not in other.tags:
			ret["tags"][tag] = (old_value, None)

	if first.hero_power != other.hero_power:
		ret["hero_power"] = (first.hero_power, other.hero_power)

	if first.entourage != other.entourage:
		added = sorted(k for k in other.entourage if k not in first.entourage)
		deleted = sorted(k for k in first.entourage if k not in other.entourage)
		ret["entourage"] = (added, deleted)

	return ret


def get_playreqs(cards):
	ret = set()
	for card in cards:
		for playreq in card.requirements:
			ret.add(playreq)
	return ret


def get_tags(cards):
	ret = set()
	for card in cards:
		for tag in card.tags:
			ret.add(tag)
	return ret


def print_enum_diff(key, before, after):
	if before is None:
		print("  - ADDED %s = %r" % (key, after))
	elif after is None:
		print("  - DELETED %s (was: %r)" % (key, before))
	else:
		print("  - CHANGED %s: %r -> %r" % (key, before, after))


def print_report(first, other):
	new_cards = {k: v for k, v in other.items() if k not in first}
	deleted_cards = {k: v for k, v in first.items() if k not in other}

	if new_cards:
		print("%i new cards:" % (len(new_cards)))
		for id, card in sorted(new_cards.items()):
			print("* %r (%s): %s, %s - %r" % (card.name, id, card.card_set, card.type, card.description))
		print()

	if deleted_cards:
		print("%i deleted cards:" % (len(deleted_cards)))
		for id, card in sorted(deleted_cards.items()):
			print("* %r (%s)" % (card.name, id))
		print()

	changed_cards = {}
	# Find changed cards
	for id, card in first.items():
		if id in deleted_cards:
			# Skip over deleted cards
			continue
		diff = card_diff(card, other[id])
		if any(diff.values()):
			changed_cards[card] = diff

	if changed_cards:
		print("%i changed cards:" % (len(changed_cards)))
		for card, diff in sorted(changed_cards.items(), key=lambda t: t[0].id):
			print("* %s (%s)" % (card.name, card.id))
			for tag, value in diff["tags"].items():
				print_enum_diff(tag, *value)

			for pr, value in diff["play_requirements"].items():
				print_enum_diff(pr, *value)

			if diff["hero_power"]:
				print("  - UPDATED HERO POWER: %r -> %r" % diff["hero_power"])

			if diff["entourage"]:
				added, removed = diff["entourage"]
				print("  - UPDATED ENTOURAGE:")
				if added:
					print("    * ADDED: %s" % (", ".join(repr(other[id]) for id in added)))
				if removed:
					print("    * REMOVED: %s" % (", ".join(repr(first[id]) for id in removed)))

		print()

	first_tags = get_tags(first.values())
	other_tags = get_tags(other.values())
	new_tags = [k for k in other_tags if k not in first_tags]
	if new_tags:
		print("%i new GameTag:" % (len(new_tags)))
		print(", ".join(repr(tag) for tag in new_tags))
		print()

	first_playreqs = get_playreqs(first.values())
	other_playreqs = get_playreqs(other.values())
	new_playreqs = [k for k in other_playreqs if k not in first_playreqs]
	if new_playreqs:
		print("%i new PlayReq:" % (len(new_playreqs)))
		print(", ".join(repr(pr) for pr in new_playreqs))
		print()


def main():
	p = ArgumentParser()
	p.add_argument("first", nargs=1, type=str)
	p.add_argument("other", nargs=1, type=str)
	args = p.parse_args(sys.argv[1:])

	first, first_xml = load_cardxml(args.first[0])
	other, other_xml = load_cardxml(args.other[0])

	print_report(first, other)


if __name__ == "__main__":
	main()
