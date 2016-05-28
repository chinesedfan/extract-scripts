#!/usr/bin/env python
import os
import sys
import unitypack
from argparse import ArgumentParser


def handle_asset(asset, textures, cards):
	for obj in asset.objects.values():
		if obj.type == "AssetBundle":
			d = obj.read()
			for entry in d["m_Container"]:
				path = entry["first"].lower()
				asset = entry["second"]["asset"]
				if not path.startswith("final/assets"):
					continue
				textures[path] = asset


def handle_cards_asset(asset, cards):
	for obj in asset.objects.values():
		if obj.type == "GameObject":
			d = obj.read()
			cardid = d.name
			if cardid in ("CardDefTemplate", "HiddenCard"):
				# not a real card
				cards[cardid] = ""
				continue
			carddef = d.component[1]["second"].resolve()
			path = carddef["m_PortraitTexturePath"]
			if path:
				path = "final/" + path
			cards[cardid] = path.lower()


def main():
	p = ArgumentParser()
	p.add_argument("--outdir", nargs="?", default="")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument("files", nargs="+")
	args = p.parse_args(sys.argv[1:])

	textures = {}
	cards = {}

	env = unitypack.UnityEnvironment()

	for file in args.files:
		with open(file, "rb") as f:
			bundle = unitypack.load(f, env)

		for asset in bundle.assets:
			if asset.name.startswith("CAB-cards"):
				handle_cards_asset(asset, cards)
			else:
				handle_asset(asset, textures, cards)

	print("Found %i cards, %i textures including %i unique in use." % (
		len(cards), len(textures), len(set(cards.values()))
	))

	for id, path in cards.items():
		if not path:
			print("%r does not have a texture" % (id))
			continue

		if path not in textures:
			print("Path %r not found for %r" % (path, id))
			continue

		pptr = textures[path]
		texture = pptr.resolve()

		png = os.path.join(args.outdir, "%s.png" % (id))
		if args.skip_existing and os.path.exists(png):
			continue
		print("%r -> %r" % (path, png))
		texture.image.save(png)


if __name__ == "__main__":
	main()
