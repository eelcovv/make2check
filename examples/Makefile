targets_txt = \
	file1.txt \
	file2.txt \
	file3.txt

targets_csv = \
	file1.csv \
	file2.csv \
	file3.csv

depends = settings.yml

default:  all

all: touch_txt touch_csv

clean: clean_txt clean_csv

touch_txt: $(targets_txt)
$(targets_txt): $(depends)
	@$(foreach file, $(targets_txt), echo "touching $(file)" && touch $(file);)

touch_csv: $(targets_csv)
$(targets_csv): $(depends)
	@$(foreach file, $(targets_csv), echo "touching $(file)" && touch $(file);)

clean_txt:
	@$(foreach file, $(targets_txt), test -f $(file) && rm -v $(file) || echo No $(file);)

clean_csv:
	@$(foreach file, $(targets_csv), test -f $(file) && rm -v $(file) || echo No $(file);)

