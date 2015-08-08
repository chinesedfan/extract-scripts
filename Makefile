MAKEFILE := $(lastword $(MAKEFILE_LIST))
BASE_DIR := $(realpath $(dir $(MAKEFILE)))
BUILD_DIR := $(BASE_DIR)/build
EXTRACTED_DIR := $(BUILD_DIR)/extracted
PROCESSED_DIR := $(BUILD_DIR)/processed
DISUNITY_BIN := disunity
EXTRACT_MPQ_BIN := $(BASE_DIR)/extract_mpq.py
PROCESS_CARDXML_BIN := $(BASE_DIR)/process_cardxml.py


.SUFFIXES:
.PHONY: extract process clean

all: extract process

extract:
	$(EXTRACT_MPQ_BIN) $(EXTRACTED_DIR)
	$(DISUNITY_BIN) --recursive extract $(EXTRACTED_DIR)

process:
	mkdir -p $(PROCESSED_DIR)
	@for dir in $(EXTRACTED_DIR)/*; do \
		$(MAKE) -f $(MAKEFILE) -B $(subst $(EXTRACTED_DIR),$(PROCESSED_DIR),$$dir); \
	done

clean:
	test -d $(BUILD_DIR) && rm -rf $(BUILD_DIR)

$(PROCESSED_DIR)/%: $(EXTRACTED_DIR)/%

$(EXTRACTED_DIR)/%:
	$(eval buildnum := $(notdir $@))
	$(eval outdir := $(PROCESSED_DIR)/$(buildnum))
	$(eval TextAsset := $(shell find $@ -name TextAsset -type d))
	@mkdir -p $(outdir)
	@$(PROCESS_CARDXML_BIN) $(TextAsset) $(outdir)/CardDefs.xml
	@test -d $@/DBF && cp -rf $@/DBF $(outdir) || exit 0
