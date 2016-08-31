#!/usr/bin/env python
import os
import sys
import unitypack
from argparse import ArgumentParser
from unitypack.environment import UnityEnvironment
from PIL import Image, ImageOps


def handle_asset(asset, textures, cards):
	for obj in asset.objects.values():
		if obj.type == "AssetBundle":
			d = obj.read()
			for path, obj in d["m_Container"]:
				path = path.lower()
				asset = obj["asset"]
				if not path.startswith("final/"):
					path = "final/" + path
				if not path.startswith("final/assets"):
					continue
				textures[path] = asset

		elif obj.type == "GameObject":
			d = obj.read()
			cardid = d.name
			if cardid in ("CardDefTemplate", "HiddenCard"):
				# not a real card
				cards[cardid] = {"path": "", "tile": ""}
				continue
			if len(d.component) != 2:
				# Not a CardDef
				continue
			carddef = d.component[1][1].resolve()
			if not isinstance(carddef, dict) or "m_PortraitTexturePath" not in carddef:
				# Not a CardDef
				continue
			path = carddef["m_PortraitTexturePath"]
			if path:
				path = "final/" + path

			tile = carddef.get("m_DeckCardBarPortrait")
			if tile:
				tile = tile.resolve()
			cards[cardid] = {
				"path": path.lower(),
				"tile": tile.saved_properties if tile else {},
			}


def extract_info(files):
	cards = {}
	textures = {}
	env = UnityEnvironment()

	for file in files:
		print("Reading %r" % (file))
		with open(file, "rb") as f:
			bundle = unitypack.load(f, env)

		for asset in bundle.assets:
			print("Parsing %r" % (asset.name))
			handle_asset(asset, textures, cards)

	return cards, textures


# Deck tile generation
TEX_COORDS = [(0.0, 0.3856), (1.0, 0.6144)]
OUT_DIM = 256
OUT_WIDTH = round(TEX_COORDS[1][0] * OUT_DIM - TEX_COORDS[0][0] * OUT_DIM)
OUT_HEIGHT = round(TEX_COORDS[1][1] * OUT_DIM - TEX_COORDS[0][1] * OUT_DIM)


def get_rect(ux, uy, usx, usy, sx, sy, ss, tex_dim=512):
	# calc the coords
	tl_x = ((TEX_COORDS[0][0] + sx) * ss) * usx + ux
	tl_y = ((TEX_COORDS[0][1] + sy) * ss) * usy + uy
	br_x = ((TEX_COORDS[1][0] + sx) * ss) * usx + ux
	br_y = ((TEX_COORDS[1][1] + sy) * ss) * usy + uy

	# adjust if x coords cross-over
	horiz_delta = tl_x - br_x
	if horiz_delta > 0:
		tl_x -= horiz_delta
		br_x += horiz_delta

	# get the bar rectangle at tex_dim size
	x = round(tl_x * tex_dim)
	y = round(tl_y * tex_dim)
	width = round(abs((br_x - tl_x) * tex_dim))
	height = round(abs((br_y - tl_y) * tex_dim))

	# adjust x and y, so that texture is "visible"
	x = (x + width) % tex_dim - width
	y = (y + height) % tex_dim - height

	# ??? to cater for some special cases
	min_visible = tex_dim / 4
	while x + width < min_visible:
		x += tex_dim
	while y + height < 0:
		y += tex_dim

	# ensure wrap around is used
	if x < 0:
		x += tex_dim

	return (x, y, width, height)


def generate_tile_image(img, tile):
	# tile the image horizontally (x2 is enough),
	# some cards need to wrap around to create a bar (e.g. Muster for Battle),
	# also discard alpha channel (e.g. Soulfire, Mortal Coil)
	tiled = Image.new("RGB", (img.width * 2, img.height))
	tiled.paste(img, (0, 0))
	tiled.paste(img, (img.width, 0))

	x, y, width, height = get_rect(
		tile["m_TexEnvs"]["_MainTex"]["m_Offset"]["x"],
		tile["m_TexEnvs"]["_MainTex"]["m_Offset"]["y"],
		tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["x"],
		tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["y"],
		tile["m_Floats"].get("_OffsetX", 0.0),
		tile["m_Floats"].get("_OffsetY", 0.0),
		tile["m_Floats"].get("_Scale", 1.0),
		img.width
	)

	bar = tiled.crop((x, y, x + width, y + height))
	bar = ImageOps.flip(bar)
	# negative x scale means horizontal flip
	if tile["m_TexEnvs"]["_MainTex"]["m_Scale"]["x"] < 0:
		bar = ImageOps.mirror(bar)

	return bar.resize((OUT_WIDTH, OUT_HEIGHT), Image.LANCZOS)


def get_dir(basedir, dirname):
	ret = os.path.join(basedir, dirname)
	if not os.path.exists(ret):
		os.makedirs(ret)
	return ret


def get_filename(basedir, dirname, name, ext=".png"):
	dirname = get_dir(basedir, dirname)
	filename = name + ext
	path = os.path.join(dirname, filename)
	return path, os.path.exists(path)


def main():
	p = ArgumentParser()
	p.add_argument("--outdir", nargs="?", default="")
	p.add_argument("--skip-existing", action="store_true")
	p.add_argument("files", nargs="+")
	args = p.parse_args(sys.argv[1:])

	cards, textures = extract_info(args.files)
	paths = [card["path"] for card in cards.values()]
	print("Found %i cards, %i textures including %i unique in use." % (
		len(cards), len(textures), len(set(paths))
	))

	orig_dir = "orig"
	thumb_sizes = (256, 512)
	tiles_dir = "tiles"

	for id, values in cards.items():
		path = values["path"]
		print("Parsing %r (%r)" % (id, path))
		if not path:
			print("%r does not have a texture" % (id))
			continue

		if path not in textures:
			print("Path %r not found for %r" % (path, id))
			continue

		pptr = textures[path]
		texture = pptr.resolve()
		flipped = None

		filename, exists = get_filename(args.outdir, orig_dir, id)
		if not (args.skip_existing and exists):
			print("-> %r" % (filename))
			flipped = ImageOps.flip(texture.image).convert("RGB")
			flipped.save(filename)

		if values["tile"]:
			filename, exists = get_filename(args.outdir, tiles_dir, id)
			if not (args.skip_existing and exists):
				tile_texture = generate_tile_image(texture.image, values["tile"])
				print("-> %r" % (filename))
				tile_texture.save(filename)

		for sz in thumb_sizes:
			thumb_dir = "%ix" % (sz)
			filename, exists = get_filename(args.outdir, thumb_dir, id, ext=".jpg")
			if not (args.skip_existing and exists):
				if not flipped:
					flipped = ImageOps.flip(texture.image).convert("RGB")
				thumb_texture = flipped.resize((sz, sz))
				print("-> %r" % (filename))
				thumb_texture.save(filename)


if __name__ == "__main__":
	main()
