from django import template

register = template.Library()


@register.inclusion_tag('js/page_language_urls.html')
def js_page_language_urls(page):
	language_list = []
	if page:
		for lang in page.get_languages():
			short_lang, locale = lang.split('-')
			language_list.append({
				'lang': lang,
				'short_lang': short_lang,
				'url': page.get_absolute_url(language=lang)
			})

	return {
		'language_list': language_list
	}
