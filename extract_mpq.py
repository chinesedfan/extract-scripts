#!/usr/bin/env python
import os
import re
import mpq


BASEPATH = "HSB/4944.direct"
EXTRACT = [
	"Hearthstone.exe",
	"Data/Win/cardxml0.unity3d",
	"Hearthstone_Data/Managed/Assembly-CSharp.dll",
	"Hearthstone_Data/Managed/Assembly-CSharp-firstpass.dll",
	"DBF/ACHIEVE.xml",
	"DBF/ADVENTURE.xml",
	"DBF/ADVENTURE_DATA.xml",
	"DBF/ADVENTURE_MISSION.xml",
	"DBF/ADVENTURE_MODE.xml",
	"DBF/BANNER.xml",
	"DBF/BOARD.xml",
	"DBF/BOOSTER.xml",
	"DBF/CARD.xml",
	"DBF/CARD_BACK.xml",
	"DBF/FIXED_REWARD.xml",
	"DBF/FIXED_REWARD_ACTION.xml",
	"DBF/FIXED_REWARD_MAP.xml",
	"DBF/HERO.xml",
	"DBF/SCENARIO.xml",
	"DBF/SEASON.xml",
	"DBF/WING.xml",

]
MPQ_REGEX = re.compile(r"hs-(\d+)-(\d+)-Win-final.MPQ")


def extract(mpq, build):
	for path in EXTRACT:
		if path not in mpq:
			print("Skipping %r (not found)" % (path))
			continue
		data = mpq.open(path).read()
		extract_path = os.path.join("extracted", str(build), path)
		dirname = os.path.dirname(extract_path)
		if not os.path.exists(dirname):
			os.makedirs(dirname)
		print("Writing to %r" % (extract_path))

		with open(extract_path, "wb") as f:
			f.write(data)


def get_builds(path):
	builds = {}
	for path in os.listdir(path):
		sre = MPQ_REGEX.match(path)
		if sre:
			base, build = sre.groups()
			base = int(base)
			if base not in builds:
				builds[base] = []
			builds[base].append(int(build))
	return builds


def get_build_chains(builds):
	chains = []
	for base_build in builds[0]:
		chain = []

		def get_build_chain(build):
			chain.append(build)
			if build in builds:
				return get_build_chain(builds[build][0])
			return chain

		chains.append(get_build_chain(base_build))

	return chains


def extract_chain(chain):
	base_build = 0
	mpqname = os.path.join(BASEPATH, "base-Win.MPQ")
	print("Opening: %r" % (mpqname))
	base = mpq.MPQFile(mpqname)
	for build in chain:
		mpqname = "hs-%i-%i-Win-final.MPQ" % (base_build, build)
		print("Opening: %r" % (mpqname))
		base.patch(os.path.join(BASEPATH, "Updates", mpqname))
		extract(base, build)
		base_build = build


def main():
	builds = get_builds(os.path.join(BASEPATH, "Updates"))
	chains = get_build_chains(builds)
	for chain in chains:
		extract_chain(chain)


if __name__ == "__main__":
	main()
