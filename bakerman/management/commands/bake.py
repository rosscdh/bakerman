import os
import shutil
from django.conf import settings
from optparse import make_option
from django.core import management
from django.core.urlresolvers import get_callable
from django.core.exceptions import ViewDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from django.test.client import Client
from urlparse import urlparse

from cms.models import Page

import re


custom_options = (
    make_option(
        "--slugs",
        action="store",
        dest="slugs",
        default='',
        help="Specify a list of page slugs to be built --slugs index,page-slug-name"
    ),
    make_option(
        "--delete-build-dir",
        action="store",
        dest="delete_build_dir",
        default=True,
        help="Should the entire build_dir be removed"
    ),
    make_option(
        "--build-dir",
        action="store",
        dest="build_dir",
        default='',
        help="Specify the path of the build directory. Will use settings.BUILD_DIR by default."
    ),
    make_option(
        "--skip-static",
        action="store_true",
        dest="skip_static",
        default=False,
        help="Skip collecting the static files when building."
    ),
    make_option(
        "--skip-media",
        action="store_true",
        dest="skip_media",
        default=False,
        help="Skip collecting the media files when building."
    ),
)


class Command(BaseCommand):
    page_name = 'index.html'
    help = 'Bake out a site as flat files in the build directory'
    option_list = BaseCommand.option_list + custom_options
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in settings.py or provide it with --build-dir"
    views_unconfig_msg = "Bakery views unconfigured. Set BAKERY_VIEWS in settings.py or provide a list as arguments."

    def handle(self, *args, **options):
        """
        Making it happen.
        """
        self.verbosity = int(options.get('verbosity'))

        self.filters = {
            'published': True
        }

        # Figure out if we should build specific pages
        if options.get("slugs"):
            self.slugs = options.get("slugs").split(',')
            self.filters['title_set__slug__in'] = self.slugs

            # dont delete the entire dir
            options["delete_build_dir"] = False

        # Figure out what build directory to use
        if options.get("build_dir"):
            self.build_dir = options.get("build_dir")
            settings.BUILD_DIR = self.build_dir
        else:
            if not hasattr(settings, 'BUILD_DIR'):
                raise CommandError(self.build_unconfig_msg)
            self.build_dir = settings.BUILD_DIR

        self.delete_build_dir = options.get("delete_build_dir")

        # Destroy the build directory, if it exists
        if self.delete_build_dir:
            if self.verbosity > 1:
                print "Creating build directory"
            if os.path.exists(self.build_dir):
                shutil.rmtree(self.build_dir)
            
            # Then recreate it from scratch
            os.makedirs(self.build_dir)
        
        # Build up static files
        if not options.get("skip_static"):
            if self.verbosity > 1:
                print "Creating static directory"
            management.call_command(
                "collectstatic",
                interactive=False,
                verbosity=0
            )
            if os.path.exists(settings.STATIC_ROOT) and settings.STATIC_URL:
                static_dir = os.path.join(self.build_dir, settings.STATIC_URL[1:])
                if os.path.exists(static_dir):
                    shutil.rmtree(static_dir)
                shutil.copytree(
                    settings.STATIC_ROOT,
                    static_dir
                )

        # Build the media directory
        if not options.get("skip_media"):
            if self.verbosity > 1:
                print "Building media directory"
            media_dir = os.path.join(self.build_dir, settings.MEDIA_URL[1:])
            if os.path.exists(media_dir):
                shutil.rmtree(media_dir)
            if os.path.exists(settings.MEDIA_ROOT) and settings.MEDIA_URL:
                shutil.copytree(
                    settings.MEDIA_ROOT,
                    media_dir
                )

        # Figure out what views we'll be using
        c = Client()
        for p in Page.objects.select_related('title').filter(**self.filters).distinct():
            self.build(c, p)

        self.primary_lang()

    def build(self, render_client, page):
        base_url = page.get_absolute_url()  # standard url used for all pages
        for title in page.title_set.all():
            if self.verbosity > 1:
                print 'Building (%d) %s - %s' % (title.pk, title, title.language)
            page = title.page
            lang_long = title.language
            lang = lang_long.split("-")[0]

            url = page.get_absolute_url(language=lang_long)

            if self.verbosity > 1:
                print "Building %s" % url

            url = '/%s%s' % (lang_long, url)
            html = str(render_client.get(url))
            html = "\n".join(html.split('\n\n', 1)[1:]).strip()

            # change to path_url if you want language specific urls
            o = urlparse(base_url)

            build_path = os.path.join(self.build_dir, lang, *o.path.split("/"))
            # ensure index.html at end of build_path
            file_path = os.path.join(build_path[:-1] if build_path[-1] == "/" else build_path, self.page_name)

            # Make sure the directory exists
            os.path.exists(build_path) or os.makedirs(build_path)
            # Write out the data
            outfile = open(file_path, 'w')
            outfile.write(self.process_html_actions(html))
            outfile.close()

    def process_html_actions(self, html):
        """ Process elements in the html that require the bake process to modify """
        prog = re.compile(r'/\*enable-on-bake\*(?P<action>.+)\*\/')
        result = prog.findall(html)
        if len(result) > 0:
            for i in result:
                html = re.sub(r'/\*enable-on-bake\*%s\*\/' % (re.escape(i),), result[0], html)
        return html

    def primary_lang(self):
        """ Move the primary settings.language copy into the root of the static
        site, but leave the original lang dirs in place """
        lang = settings.LANGUAGE_CODE.split("-")[0]
        src_path = os.path.join(self.build_dir, lang)

        os.path.exists(src_path) or os.makedirs(src_path)

        for f in os.listdir(src_path):
            file_path = os.path.join(src_path, f)
            if os.path.isdir(file_path):
                dir_name = os.path.split(file_path)[1]
                target_dir = os.path.join(self.build_dir, dir_name)
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                shutil.copytree(file_path, target_dir)
            else:
                shutil.copy(file_path, self.build_dir)
