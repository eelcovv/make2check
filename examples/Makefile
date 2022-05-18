targets = \
	file1.txt \
	file2.txt \
	file3.txt

depends = settings.yml

touch: $(targets)
$(targets): $(depends)
	@$(foreach file, $(targets), echo "touching $(file)" && touch $(file);)

clean:
	@$(foreach file, $(targets), test -f $(file) && rm -v $(file) || echo No $(file);)

