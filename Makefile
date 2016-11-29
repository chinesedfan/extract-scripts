SHELL:=/bin/bash -O globstar
MAKEFILE := $(lastword $(MAKEFILE_LIST))
BASE_DIR := $(realpath $(dir $(MAKEFILE)))
BUILD_DIR := $(BASE_DIR)/build
MPQ_DIR := $(BUILD_DIR)/MPQ
DECOMPILED_DIR := $(BUILD_DIR)/decompiled
EXTRACTED_DIR := $(BUILD_DIR)/extracted
PROCESSED_DIR := $(BUILD_DIR)/processed
PROTOS_DIR := $(BUILD_DIR)/protos
PROTOS_GO_DIR := $(BUILD_DIR)/go-protos
DECOMPILER_BIN := mono $(BASE_DIR)/decompiler/build/decompile.exe
EXTRACT_MPQ_BIN := $(BASE_DIR)/extract_mpq.py
PROCESS_CARDXML_BIN := $(BASE_DIR)/process_cardxml.py
PROTO_EXTRACTOR_BIN := $(BASE_DIR)/../proto-extractor/bin/Debug/proto-extractor.exe

.SUFFIXES:
.PHONY: all extract process decompile clean


all: process decompile

extract:
	$(EXTRACT_MPQ_BIN) $(MPQ_DIR) $(EXTRACTED_DIR)

process:
	@mkdir -p $(PROCESSED_DIR)
	@for dir in $(EXTRACTED_DIR)/*; do \
		$(MAKE) -f $(MAKEFILE) -B $(subst $(EXTRACTED_DIR),$(PROCESSED_DIR),$$dir)/; \
	done

decompile:
	@cd $(BASE_DIR)/decompiler && $(MAKE)
	$(MAKE) -f $(MAKEFILE) -B $(shell find -L $(EXTRACTED_DIR) -name "Assembly-CSharp*.dll" -type f)

%/Assembly-CSharp.dll:
	$(eval buildnum := $(notdir $(realpath $(dir $@)/../..)))
	$(DECOMPILER_BIN) $@ $(DECOMPILED_DIR)/$(buildnum)
	@# $(PROTO_EXTRACTOR_BIN) -o $(PROTOS_DIR)/$(buildnum) -g $(PROTOS_GO_DIR)/$(buildnum) $@

%/Assembly-CSharp-firstpass.dll:
	$(eval buildnum := $(notdir $(realpath $(dir $@)/../..)))
	$(DECOMPILER_BIN) $@ $(DECOMPILED_DIR)/$(buildnum)
	@# $(PROTO_EXTRACTOR_BIN) -o $(PROTOS_DIR)/$(buildnum) -g $(PROTOS_GO_DIR)/$(buildnum) $@

clean:
	test -d $(BUILD_DIR) && rm -rf $(BUILD_DIR)

$(PROCESSED_DIR)/%/: $(EXTRACTED_DIR)/%/

$(EXTRACTED_DIR)/%/:
	$(eval buildnum := $(notdir $(patsubst %/,%,$@)))
	$(eval outdir := $(PROCESSED_DIR)/$(buildnum))
	$(eval bundles := $(shell find -L $@/Data -name '*.unity3d' -type f))
	$(eval DBF := $(shell find -L $@ -name DBF -type d))
	@mkdir -p $(outdir)
	@if [ -z "$(DBF)" ]; then \
		$(PROCESS_CARDXML_BIN) -o $(outdir)/CardDefs.xml $(bundles); \
	else \
		$(PROCESS_CARDXML_BIN) -o $(outdir)/CardDefs.xml --dbf-dir $(DBF) $(bundles); \
		cp -rf $@/DBF $(outdir); \
	fi
	@cp -rf $@/Strings $(outdir)
