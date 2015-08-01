#!/bin/bash

BASEDIR="$(realpath $(dirname $0))"
EXTRACTED_DIR="$BASEDIR/build/extracted"
PROCESSED_DIR="$BASEDIR/build/processed"


"$BASEDIR/extract_mpq.py" "$EXTRACTED_DIR"

for dir in "$EXTRACTED_DIR"/*; do
	build=$(basename "$dir")
	echo "Extracting files for $build"
	outdir="$PROCESSED_DIR/$build"

	mkdir -p "$outdir"
	if [[ -e "$dir/Data/cards.unity3d" ]]; then
		# Old-style card extraction
		disunity extract "$dir/Data/cards.unity3d"
		mv "$dir"/Data/cards/CAB-*/TextAsset "$dir"
	else
		disunity extract "$dir/Data/Win/cardxml0.unity3d"
		mv "$dir/Data/Win/cardxml0/CAB-cardxml0/TextAsset" "$dir"
	fi
	"$BASEDIR/process_cardxml.py" "$dir/TextAsset" "$dir/CardDefs.xml"
	mv "$dir/CardDefs.xml" "$outdir"
	mv "$dir/DBF" "$outdir"
	rm -rf "$dir/TextAsset"
done
