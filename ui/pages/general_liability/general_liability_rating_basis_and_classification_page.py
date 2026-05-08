from ui.pages.common.base_page import BasePage


class GeneralLiabilityRatingBasisAndClassificationPage(BasePage):
    """General Liability rating basis and classification page."""

    def __init__(self, page):
        super().__init__(page)

        self.gl_class_description = page.get_by_role("combobox", name="GL Class Description*")
        self.exposure = page.get_by_role("textbox", name="Exposure *")
        self.rating_save_button = page.get_by_role("button", name="save changes")

        self.rate_quote_button = page.get_by_role("button", name=">>> rate quote")
        self.request_issue_button = page.get_by_role("button", name=">>> request issue")
        self.next_button = page.get_by_role("button", name=">>> next")

    def rating_basis_and_classification_steps(self, data):
        self.open_rating_basis_and_classification(data)
        self.select_class_code(data)
        self.set_gl_class_description(data)
        self.set_exposure(data)
        self.click_rating_save()

    def inventory_dropdown_options(self, data):
        self.open_rating_basis_and_classification(data)
        return {
            "GLClassCode": self.collect_visible_role_texts("option"),
            "GLClassDescription": self.collect_extjs_options(self.gl_class_description),
        }

    def inventory_and_fill(self, data):
        options = {}
        self.open_rating_basis_and_classification(data)
        options["GLClassCode"] = self.collect_visible_role_texts("option")
        self.select_class_code(data)
        options["GLClassDescription"] = self.collect_extjs_options(self.gl_class_description)
        self.set_gl_class_description(data)
        self.set_exposure(data)
        self.click_rating_save()
        return options

    def open_rating_basis_and_classification(self, data):
        self.with_optional_oneshield_response(lambda: self._click_visible_link_or_tree_node(data["LiabilityCity"]))
        self.wait_for_loader_to_disappear()

    def select_class_code(self, data):
        self.with_optional_oneshield_response(
            lambda: self._click_visible_tree_or_option_node(data["GLClassCode"], exact=False)
        )
        self.wait_for_loader_to_disappear()

    def set_gl_class_description(self, data):
        self._select_gl_class_description(data["GLClassDescription"])
        self.wait_for_loader_to_disappear()

    def set_exposure(self, data):
        self.with_optional_oneshield_response(lambda: self.smart_fill(self.exposure, data["Exposure"]))
        self.wait_for_loader_to_disappear()

    def click_rating_save(self):
        self._click_and_wait(self.rating_save_button, wait_for_response=True)

    def click_rate_quote(self):
        self._click_and_wait(self.rate_quote_button, wait_for_response=True)

    def click_request_issue(self):
        self._click_and_wait(self.request_issue_button, wait_for_response=True)

    def click_next(self):
        self._click_and_wait(self.next_button, wait_for_response=False)


    def _click_visible_link_or_tree_node(self, text):
        self._click_visible_tree_or_option_node(text, exact=False)

    def _select_gl_class_description(self, value):
        class_code = str(value).split(":", 1)[0].strip()
        self.gl_class_description.scroll_into_view_if_needed()
        self.gl_class_description.click()
        self.gl_class_description.fill("")
        self.gl_class_description.fill(class_code)

        self.page.wait_for_function(
            """(code) => [...document.querySelectorAll('.x-boundlist-item')]
                .some(el => {
                    const r = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const label = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                    return r.width > 0 && r.height > 0
                        && style.visibility !== 'hidden'
                        && style.display !== 'none'
                        && label.startsWith(code);
                })""",
            arg=class_code,
            timeout=30000,
        )

        self.with_optional_oneshield_response(
            lambda: self.page.evaluate(
                """(code) => {
                    const items = [...document.querySelectorAll('.x-boundlist-item')];
                    const visible = items.filter(el => {
                        const r = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return r.width > 0 && r.height > 0
                            && style.visibility !== 'hidden'
                            && style.display !== 'none';
                    });
                    const match = visible.find(el => {
                        const label = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                        return label.startsWith(code);
                    });
                    if (match) {
                        match.click();
                        return;
                    }
                    throw new Error('Visible GL class description option not found for code: ' + code);
                }""",
                class_code,
            )
        )

    def _click_visible_tree_or_option_node(self, text, exact=True):
        self.page.wait_for_function(
            """([needle, exact]) => [...document.querySelectorAll('a, li, [role="link"], [role="treeitem"], [role="option"]')]
                .some(el => {
                    const r = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const label = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                    return r.width > 0 && r.height > 0
                        && style.visibility !== 'hidden'
                        && style.display !== 'none'
                        && (exact ? label === needle : (label === needle || label.includes(needle)));
                })""",
            arg=[text, exact],
            timeout=30000,
        )

        self.page.evaluate(
            """([needle, exact]) => {
                const nodes = [...document.querySelectorAll('a, li, [role="link"], [role="treeitem"], [role="option"]')];
                const visible = nodes.filter(el => {
                    const r = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0
                        && style.visibility !== 'hidden'
                        && style.display !== 'none';
                });
                const match = visible.find(el => {
                    const label = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                    return exact ? label === needle : (label === needle || label.includes(needle));
                });
                if (match) {
                    match.click();
                    return;
                }
                throw new Error('Visible clickable node not found: ' + needle);
            }""",
            [text, exact],
        )
