SHELL:=/bin/bash -O globstar
MAKEFILE := $(lastword $(MAKEFILE_LIST))
BASE_DIR := $(realpath $(dir $(MAKEFILE)))
BUILD_DIR := $(BASE_DIR)/build
DECOMPILED_DIR := $(BUILD_DIR)/decompiled
EXTRACTED_DIR := $(BUILD_DIR)/extracted
PROCESSED_DIR := $(BUILD_DIR)/processed
DECOMPILER_BIN := mono $(BASE_DIR)/decompiler/build/decompile.exe
DISUNITY_BIN := disunity
EXTRACT_MPQ_BIN := $(BASE_DIR)/extract_mpq.py
PROCESS_CARDXML_BIN := $(BASE_DIR)/process_cardxml.py

.SUFFIXES:
.PHONY: all extract process decompile clean


all: extract process decompile

extract:
	$(EXTRACT_MPQ_BIN) $(EXTRACTED_DIR)
	$(DISUNITY_BIN) --recursive extract $(EXTRACTED_DIR)/**/*.unity3d

process:
	@mkdir -p $(PROCESSED_DIR)
	@for dir in $(EXTRACTED_DIR)/*; do \
		$(MAKE) -f $(MAKEFILE) -B $(subst $(EXTRACTED_DIR),$(PROCESSED_DIR),$$dir)/; \
	done

decompile:
	@cd $(BASE_DIR)/decompiler && $(MAKE)
	$(MAKE) -f $(MAKEFILE) -B $(shell find $(EXTRACTED_DIR) -name "Assembly-CSharp*.dll" -type f)

%/Assembly-CSharp.dll:
	$(eval buildnum := $(notdir $(realpath $(dir $@)/../..)))
	$(DECOMPILER_BIN) $@ $(DECOMPILED_DIR)/$(buildnum)

%/Assembly-CSharp-firstpass.dll:
	$(eval buildnum := $(notdir $(realpath $(dir $@)/../..)))
	$(DECOMPILER_BIN) $@ $(DECOMPILED_DIR)/$(buildnum)

clean:
	test -d $(BUILD_DIR) && rm -rf $(BUILD_DIR)

$(PROCESSED_DIR)/%/: $(EXTRACTED_DIR)/%/

$(EXTRACTED_DIR)/%/:
	$(eval buildnum := $(notdir $(patsubst %/,%,$@)))
	$(eval outdir := $(PROCESSED_DIR)/$(buildnum))
	$(eval TextAsset := $(shell find $@ -name TextAsset -type d))
	@mkdir -p $(outdir)
	@$(PROCESS_CARDXML_BIN) $(TextAsset) $(outdir)/CardDefs.xml
	@test -d $@/DBF && cp -rf $@/DBF $(outdir) || exit 0
