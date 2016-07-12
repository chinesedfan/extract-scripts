#!/bin/bash
BASEDIR="$(readlink -f $(dirname $0))"
EXTRACTED_DIR="$BASEDIR/build/extracted"
PROCESSED_DIR="$BASEDIR/build/processed"
DECOMPILED_DIR="$BASEDIR/build/decompiled"

if [[ -z $1 ]]; then
	echo "Usage: $0 [BUILD]"
	exit 1
fi

BUILD=$1

make -B \
	"$EXTRACTED_DIR/$BUILD/" \
	"$EXTRACTED_DIR/$BUILD/Hearthstone_Data/Managed/Assembly-CSharp.dll" \
	"$EXTRACTED_DIR/$BUILD/Hearthstone_Data/Managed/Assembly-CSharp-firstpass.dll"

./commit.sh $BUILD
