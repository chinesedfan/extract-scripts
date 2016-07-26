#!/bin/bash

set -e

BUILD="$1"

isnum='^[0-9]+$'
if ! [[ $BUILD =~ $isnum ]]; then
	>&2 echo "USAGE: $0 [BUILD]"
	exit 1
fi

# Base directory for large data files
DATADIR="/mnt/home/ngdp"

# Directory storing the 'hsb' blte config
HSBDIR="$DATADIR/hsb"

# Extraction path for 'hsb' blte
NGDP_OUT="$HSBDIR/out"

# Directory storing the build data files
HSBUILDDIR="$DATADIR/data/ngdp/hsb/$BUILD"

# Directory that contains card textures
CARDARTDIR="$DATADIR/card-art"

# HearthstoneJSON generated files directory
HSJSONDIR="/srv/http/api.hearthstonejson.com/html/v1/$BUILD"

# extract-scripts repo directory
EXTRACT_SCRIPTS="$HOME/projects/extract-scripts"

# Symlink file for extracted data
EXTRACT_SCRIPTS_LINKFILE="$EXTRACT_SCRIPTS/build/extracted/$BUILD"

# Patch downloader
BLTE_BIN="$HOME/bin/blte.exe"

# Autocommit script
COMMIT_BIN="$EXTRACT_SCRIPTS/commit.sh"

# manage.py from HSReplay.net
MANAGEPY_ENV="/srv/http/hsreplay.net/virtualenv/bin/python"
MANAGEPY_BIN="/srv/http/hsreplay.net/source/manage.py"

# Card texture extraction/generation script
TEXTUREGEN_BIN="$EXTRACT_SCRIPTS/generate_card_textures.py"

# Smartdiff generation script
SMARTDIFF_BIN="$EXTRACT_SCRIPTS/smartdiff_cardxml.py"

# Smartdiff output file
SMARTDIFF_OUT="$HOME/smartdiff-$BUILD.txt"

# hscode/hsdata git repositories
HSCODE_GIT="$EXTRACT_SCRIPTS/hscode.git"
HSDATA_GIT="$EXTRACT_SCRIPTS/hsdata.git"

# CardDefs.xml path for the build
CARDDEFS_XML="$HSDATA_GIT/CardDefs.xml"


echo "Updating repositories"
declare -a repos=("$EXTRACT_SCRIPTS")
for repo in $repos; do
	git -C "$repo" pull
done

if ! grep -q "$BUILD" "$COMMIT_BIN"; then
	>&2 echo "$BUILD is not present in $COMMIT_SCRIPT. Aborting."
	exit 3
fi


echo "Preparing patch directories"
if [[ -e $HSBUILDDIR ]]; then
	echo "$HSBUILDDIR already exists... skipping download checks."
else
	if ! [[ -d "$NGDP_OUT" ]]; then
		>&2 echo "No "$NGDP_OUT" directory. Run cd $HSBDIR && $BLTE_BIN"
		exit 2
	fi
	echo "Moving $NGDP_OUT to $HSBUILDDIR"
	mv "$NGDP_OUT" "$HSBUILDDIR"
fi

echo "Linking build files"
if [[ -e $EXTRACT_SCRIPTS_LINKFILE ]]; then
	echo "$EXTRACT_SCRIPTS_LINKFILE already exists, not overwriting."
else
	echo "Creating symlink to build in $EXTRACT_SCRIPTS_LINKFILE"
	ln -s -v "$HSBUILDDIR" "$EXTRACT_SCRIPTS_LINKFILE"
fi


# Panic? cardxml_raw_extract.py can extract the raw carddefs
# Coupled with a manual process_cardxml.py --raw, can gen CardDefs.xml


if ! git -C "$HSDATA_GIT" rev-parse "$BUILD" &>/dev/null; then
	echo "Extracting and decompiling the build"

	make --directory="$EXTRACT_SCRIPTS" -B \
		"$EXTRACT_SCRIPTS_LINKFILE/" \
		"$EXTRACT_SCRIPTS_LINKFILE/Hearthstone_Data/Managed/Assembly-CSharp.dll" \
		"$EXTRACT_SCRIPTS_LINKFILE/Hearthstone_Data/Managed/Assembly-CSharp-firstpass.dll"

	echo "Generating git repositories"
	"$COMMIT_BIN" "$BUILD"

	echo "Pushing to GitHub"
	git -C "$HSDATA_GIT" push --follow-tags -f
	git -C "$HSCODE_GIT" push --follow-tags -f
else
	echo "Tag $BUILD already present in $HSDATA_GIT - skipping core build generation."
fi

git -C "$HSDATA_GIT" show "$BUILD:CardDefs.xml" > /tmp/new.xml
git -C "$HSDATA_GIT" show "$BUILD~:CardDefs.xml" > /tmp/old.xml

echo "Generating smartdiff"
"$SMARTDIFF_BIN" "/tmp/new.xml" "/tmp/old.xml" > "$SMARTDIFF_OUT"
echo "Generated smartdiff in $SMARTDIFF_OUT"
rm /tmp/new.xml /tmp/old.xml


echo "Updating HearthstoneJSON"
if [[ -e $HSJSONDIR ]]; then
	echo "HearthstoneJSON is up-to-date."
else
	sudo -u www-data /var/www/hearthstonejson.sh "$BUILD"
fi


echo "Extracting card textures"
"$EXTRACT_SCRIPTS/generate_card_textures.py" "$HSBUILDDIR/Data/Win/"{card,shared}*.unity3d --outdir="$CARDARTDIR" --skip-existing
# TODO: now flip textures and convert to jpg

echo "Post-processing card textures"
for img in "$CARDARTDIR"/*.png; do
	filename=${img%.*}
	if [[ -f "$filename.jpg" ]]; then
		# If the jpg already exists, do not regenerate it
		continue
	fi
	echo "Post-processing $filename.png"
	# NOTE: -flip is needed because the textures are upside down in unity
	convert -flip "$filename.png" "$filename.jpg"
done


echo "Loading cards into the HSReplay.net database"

sudo -u www-data "$MANAGEPY_ENV" "$MANAGEPY_BIN" load_cards "$CARDDEFS_XML"

echo "Build $BUILD completed"
