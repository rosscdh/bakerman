bakerman
========

Django-CMS static site generator

A simple app to print out a static version of a django-cms site

1. add bakerman to INSTALLED_APPS
2. manage.py help bake
3. manage.py bake [options]


**note** this only works for django cms sites atm

## ToDo ##

1. loop over router urls (instead of Page objects form django-cms) and perform bake events
