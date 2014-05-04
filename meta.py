
import os
import guessit
import re

#
# Helper class to help infer meta data based on a file name and update an mp4 file with this meta data
#


class Helper(object):

    class Keys(object):
        TVShow = "show"
        TVEpisodeNumber = "episode_sort"
        TVSeasonNumber = "season_number"
        MovieTitle = "title"
        MovieYear = "date"

        # TODO: Figure out what ITunes' "Media Kind" is (TVShow / Movie)

    def __init__(self, path_to_ffmpeg=None):
        self.path_to_ffmpeg = path_to_ffmpeg if not path_to_ffmpeg is None else "/opt/local/bin/ffmpeg"
        self.allow_logging = True
        if not os.path.exists(self.path_to_ffmpeg):
            self.log("[Warning] Failed to locate ffmpeg - Please make sure you have ffmpeg installed on this system")

    def log(self, msg):
        if self.allow_logging:
            print (msg)

    #
    # MetaData Inferance using Guessit
    # (Requires guessit module)
    #

    def infer_metadata_from_movie_file(self, path_to_file):
        guess = guessit.guess_movie_info(path_to_file, info=['filename'])
        if guess is None or len(guess) == 0:
            self.log("[Warning] Failed to guess movie metadata")
            return None
        return Helper._extract_metadata_from_guessit_dict(guess, mappings={"title": Helper.Keys.MovieTitle, "year": Helper.Keys.MovieYear})

    def infer_metadata_from_tvshow_file(self, path_to_file):
        guess = guessit.guess_episode_info(path_to_file, info=['filename'])
        if guess is None or len(guess) == 0:
            self.log("[Warning] Failed to guess tv show metadata")
            return None
        return Helper._extract_metadata_from_guessit_dict(guess, mappings={"episodeNumber": Helper.Keys.TVEpisodeNumber, "season": Helper.Keys.TVSeasonNumber, "series": Helper.Keys.TVShow})

    @staticmethod
    def _extract_metadata_from_guessit_dict(guess, mappings):
        d = dict()
        for (k, v) in guess.items():
            if k in mappings:
                if type(v) is int:
                    d[mappings[k]] = str(v)
                else:
                    d[mappings[k]] = v
        return d

    #
    # Manual Inferance
    # (Note: Does not work too well atm)
    #

    def infer_metadata_from_file(self, path_to_file):
        if not os.path.exists(path_to_file):
            self.log("[Error] Failed to locate file")
            return None
        base = os.path.basename(path_to_file)
        bex = os.path.splitext(base)
        file_name = bex[0]
        file_name = Helper.santise_filename(file_name)

        regex = self._build_tv_show_regex()
        matches = re.match(regex, file_name)
        if not matches:
            self.log("[Error] Failed to understand file-name")
            return None
        return self._metadata_from_tv_show_regex_matches(matches)

    def _metadata_from_tv_show_regex_matches(self, matches):
        details = {}

        try:
            details[Helper.Keys.TVShow] = matches.group('show_name').replace('.', ' ').strip()
        except IndexError:
            pass
        try:
            details[Helper.Keys.TVSeasonNumber] = str(int(matches.group('season')))
        except IndexError:
            pass

        try:
            details[Helper.Keys.TVEpisodeNumber] = str(int(matches.group('episode')))
        except IndexError:
            pass

        if len(details) == 0:
            self.log("[Warning] Found no meta data for file")
            return None

        return details

    #  Based on tvrenamr 3.4.11 function
    def _build_tv_show_regex(self, regex=None):
        """Builds the regular expression to extract a files details.

        Custom syntax can be used in the regular expression to help specify
        parts of the episode's file name. These custom syntax snippets are
        replaced by the regular expression blocks show.

        %n - [\w\s.,_-]+ - The show name.
        %s - \d{1,2} - The season number.
        %e - \d{2} - The episode number.

        """
        series = r"(?P<show_name>[\w\s.',_-]+)"
        season = r"(?P<season>\d{1,2})"
        episode = r"(?P<episode>\d{2})"
        second_episode = r".E?(?P<episode2>\d{2})*"

        if regex is None:
            # Build default regex
            return series + r"\.[Ss]?" + season + r"[XxEe]?" + episode + second_episode

        # series name
        regex = regex.replace('%n', series)

        # season number
        # %s{n}
        if '%s{' in regex:
            self.log('Season digit number found')
            r = regex.split('%s{')[1][:1]
            self.log('Specified {0} season digits'.format(r))
            s = season.replace('1,2', r)
            regex = regex.replace('%s{' + r + '}', s)
            self.log('Season regex set: {0}'.format(s))

        # %s
        if '%s' in regex:
            regex = regex.replace('%s', season)
            self.log('Default season regex set: {0}'.format(regex))

        # episode number
        # %e{n}
        if '%e{' in regex:
            self.log('User set episode digit number found')
            r = regex.split('%e{')[1][:1]
            self.log('User specified {0} episode digits'.format(r))
            e = episode.replace('2', r)
            regex = regex.replace('%e{' + r + '}', e)
            self.log('Episode regex set: {0}'.format(e))

        # %e
        if '%e' in regex:
            regex = regex.replace('%e', episode)
            self.log('Default episode regex set: {0}'.format(regex))

        return regex

    #
    # FFMpeg
    #

    def _execute_ffmpeg(self, params):
        cmd = "%s %s" % (self.path_to_ffmpeg, params)
        os.system(cmd)

    def show(self, path_to_file):
        self._execute_ffmpeg('-i "%s"' % path_to_file)

    #
    # Utility Methods
    #

    @staticmethod
    #  Based on tvrenamr 3.4.11 function
    def santise_filename(filename):
        """
        Remove bits of the filename that cause a problem.

        Initially added to deal specifically with the issues 720[p] causes
        in filenames by appearing before or after the season/episode block.
        """
        items = (
            ('_', '.'),
            (' ', '.'),
            ('.720p', ''),
            ('.720', ''),
            ('.1080p', ''),
            ('.1080', ''),
            ('.H.264', ''),
            ('.h.264', ''),
            ('.x264', ''),
        )
        for target, replacement in items:
            filename = filename.replace(target, replacement)
        print filename
        return filename

    @staticmethod
    def replace_file_but_stick_original_in_trash(path_to_original, path_to_replacement):
        trash_path = os.path.expanduser("~/.Trash")
        cmd = 'mv "%s" "%s"' % (path_to_original, trash_path)
        os.system(cmd)
        cmd = 'mv "%s" "%s"' % (path_to_replacement, path_to_original)
        os.system(cmd)

    #
    # Metadata Setters
    # (Requires ffmpeg to work)
    #

    @staticmethod
    def _destination_path_from_input(path_to_file, destination_file):
        if destination_file is not None:
            o_file = destination_file
        else:
            ex = os.path.splitext(path_to_file)
            o_file = ex[0] + "_meta_tmp" + ex[1]
        return o_file

    def set_metadata_with_key_and_value(self, path_to_file, key, value, destination_file=None):
        o_file = Helper._destination_path_from_input(path_to_file, destination_file)
        params = '-i "%s" -metadata %s="%s" -y -codec copy "%s"' % (path_to_file, key, value, o_file)
        self._execute_ffmpeg(params)
        if destination_file is None:
            Helper.replace_file_but_stick_original_in_trash(path_to_file, o_file)

    def set_metadata_with_dict(self, path_to_file, meta_dict, destination_file=None):
        o_file = Helper._destination_path_from_input(path_to_file, destination_file)
        meta_datas = ""
        for (k, v) in meta_dict.items():
            meta_datas += '-metadata %s="%s" ' % (k, v)
        params = '-i "%s" %s -y -codec copy "%s"' % (path_to_file, meta_datas, o_file)
        self._execute_ffmpeg(params)
        if destination_file is None:
            Helper.replace_file_but_stick_original_in_trash(path_to_file, o_file)