BASEDIR="$(readlink -f $(dirname $0))"
PROCESSED_DIR="$BASEDIR/build/processed"
DECOMPILED_DIR="$BASEDIR/build/decompiled"

make -B \
	"$EXTRACTED_DIR/$BUILD/" \
	"$EXTRACTED_DIR/$BUILD/Hearthstone_Data/Managed/Assembly-CSharp.dll" \
	"$EXTRACTED_DIR/$BUILD/Hearthstone_Data/Managed/Assembly-CSharp-firstpass.dll"
