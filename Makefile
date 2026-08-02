.PHONY: content-validate content-import content-publish content-check-references content-rollback validate-content import-content publish-content check-references rollback-content

content-validate:
	npm run validate-content

content-import:
	npm run content:import

content-publish:
	npm run content:publish -- --draft "$(DRAFT)" --publisher "$(PUBLISHER)"

content-check-references:
	npm run content:check-references

content-rollback:
	npm run content:rollback -- --artifact "$(ARTIFACT)" --version "$(VERSION)" --publisher "$(PUBLISHER)" --reason "$(REASON)"

validate-content: content-validate
import-content: content-import
publish-content: content-publish
check-references: content-check-references
rollback-content: content-rollback
