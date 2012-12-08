import itertools
import re
import sys
import warnings


enableColor = True
ansiCSI = chr(27) + '['


class ANSIEscapeBuilder(object):
    def __init__(self, enableReadlineMarkers=False):
        self.nextSection = self._sections
        self.values = list()
        self.enableReadlineMarkers = enableReadlineMarkers

    def __dir__(self):
        builtinAttrs = [
                '__init__',
                '__dir__',
                '__getattr__',
                '__getitem__',
                '__str__',
                '_sections',
                ]
        if self.nextSection is not None:
            return builtinAttrs + self.nextSection.keys()

        return builtinAttrs + self._sections.keys()

    def _handleItem(self, name):
        attrOrSection = self.nextSection[name]

        if isinstance(attrOrSection, int):
            self.values.append(attrOrSection)
            self.nextSection = self._sections

        elif isinstance(attrOrSection, tuple):
            self.values.extend(attrOrSection)
            self.nextSection = self._sections

        else:
            self.nextSection = attrOrSection

        return self

    def __getattr__(self, name):
        return self._handleItem(str(name))

    def __getitem__(self, key):
        return self._handleItem(str(key))

    def __str__(self):
        rendered = ansiCSI + ";".join(map(str, self.values)) + self._postfix

        if self.enableReadlineMarkers:
            return "\001{}\002".format(rendered)
        return rendered


class _Style(ANSIEscapeBuilder):
    _postfix = 'm'
    _sections = dict(
            none=0,
            bold=1,
            faint=2,
            italic=3,
            underline=4,
            blink=5,
            fast=6,
            reverse=7,
            concealed=8,
            fg=dict(
                black=30,
                gray=30,
                grey=30,
                red=31,
                green=32,
                yellow=33,
                blue=34,
                magenta=35,
                cyan=36,
                white=37,
                bright=dict(
                    gray=90,
                    grey=90,
                    red=91,
                    green=92,
                    yellow=93,
                    blue=94,
                    magenta=95,
                    cyan=96,
                    white=97,
                    ),
                ),
            bg=dict(
                black=40,
                red=41,
                green=42,
                yellow=43,
                blue=44,
                magenta=45,
                cyan=46,
                white=47,
                bright=dict(
                    gray=100,
                    grey=100,
                    red=101,
                    green=102,
                    yellow=103,
                    blue=104,
                    magenta=105,
                    cyan=106,
                    white=107,
                    ),
                ),
            )


class ANSISingleNumberBuilder(ANSIEscapeBuilder):
    def __init__(self, enableReadlineMarkers=False):
        super(ANSISingleNumberBuilder, self).__init__(enableReadlineMarkers)
        self.values = ['']

    def _handleItem(self, name):
        if self.nextSection is not None:
            if isinstance(self.nextSection, dict):
                self.nextSection = self.nextSection[name]
            else:
                self.values.append(name + self.nextSection)
                self.nextSection = None

        else:
            self.nextSection = self._sections[name]

        return self

    def __str__(self):
        return ansiCSI.join(self.values)


class _Cursor(ANSISingleNumberBuilder):
    _sections = dict(
            up='A',
            down='B',
            right='C',
            left='D',
            forward='C',
            back='D',
            col='G',
            row='H',
            )


class _Scroll(ANSISingleNumberBuilder):
    _sections = dict(
            up='S',
            down='T',
            )


class ANSILiteralBuilder(ANSIEscapeBuilder):
    def __init__(self, enableReadlineMarkers=False):
        super(ANSILiteralBuilder, self).__init__(enableReadlineMarkers)
        self.values = ['']

    def _handleItem(self, name):
        if self.nextSection is not None:
            if isinstance(self.nextSection, dict):
                self.nextSection = self.nextSection[name]
            else:
                self.values.append(self.nextSection[name])
                self.nextSection = None

        else:
            if isinstance(self._sections[name], basestring):
                self.values.append(self._sections[name])
            else:
                self.nextSection = self._sections[name]

        return self

    def __str__(self):
        return ansiCSI.join(self.values)


class _Clear(ANSILiteralBuilder):
    _sections = dict(
            line=dict(
                start='1K',
                end='K',
                all='2K',
                ),
            screen=dict(
                start='1J',
                end='J',
                all='2J',
                ),
            )


class _EscapeBuilderFactory(object):
    def __init__(self, targetClass, **initKwargs):
        self._targetClass = targetClass
        self._initKwargs = initKwargs

    def __getattr__(self, name):
        return getattr(self._targetClass(**self._initKwargs), name)


style = _EscapeBuilderFactory(_Style)
cursor = _EscapeBuilderFactory(_Cursor)
scroll = _EscapeBuilderFactory(_Scroll)
clear = _EscapeBuilderFactory(_Clear)


class Attributes:
    (
        none,
        bold,
        faint,
        italic,
        underline,
        blink,
        fast,
        reverse,
        concealed
    ) = range(9)


class Foreground:
    (
        black,
        red,
        green,
        yellow,
        blue,
        magenta,
        cyan,
        white
    ) = range(30, 38)
    gray = black
    grey = black


class Background:
    (
        black,
        red,
        green,
        yellow,
        blue,
        magenta,
        cyan,
        white
    ) = range(40, 48)


class Special:
    reset = '%s0m' % (ansiCSI, )
    clear = '%s2J%sH' % (ansiCSI, ansiCSI)

    @staticmethod
    def move(x=1, y=1):
        return '%s%d;%dH' % (ansiCSI, x, y)


def color(*args):
    if not enableColor:
        return ''

    if len(args) > 0:
        return ansiCSI + ";".join(map(str, args)) + 'm'
    else:
        return Special.reset


def colored(text, *args):
    if len(args) == 1 and isinstance(args[0], basestring):
        return "%s%s%s" % (args[0], text, style.none)
    else:
        return color(*args) + text + color()


def write(string, *args, **kwargs):
    """This function writes ANSI color formatted strings to the given target.

    See the documentation for `colorfmt`.

    """
    suppressNewline = kwargs.pop('suppressNewline', False)

    nl = '\n'
    if suppressNewline:
        nl = ''

    target = kwargs.pop('target', sys.stdout)

    target.write(colorfmt(string, *args, **kwargs) + nl)

    if suppressNewline:
        target.flush()


def stdout(string, *args, **kwargs):
    """This function prints color-formatted strings to stdout.

    See the documentation for `colorfmt`.

    """
    kwargs.setdefault('target', sys.stdout)
    write(string,
            *args,
            **kwargs
            )


def stderr(string, *args, **kwargs):
    """This function prints color-formatted strings to stderr.

    See the documentation for `colorfmt`.

    """
    kwargs.setdefault('target', sys.stderr)
    write(string,
            *args,
            **kwargs
            )


def colorfmt(string, *args, **kwargs):
    """This function returns ANSI equivalents of color-formatted strings.

    To add a color or attribute to a string, first add something of the
    following format:
        '{style.blink.fg.red.bg.blue}'
    or:
        '{style.none}'

    Example:

        colored = colorfmt("{style.blink.fg.red.bg.blue}foo{style.none}")

    """
    return string.format(
            style=style,
            cursor=cursor,
            scroll=scroll,
            clear=clear,
            *args,
            **kwargs
            )


def promptfmt(string, *args, **kwargs):
    """This function is similar to colorfmt, except that it generates additional characters to tell readline to ignore
    the ANSI escape sequences, so that text lines up correctly when utilizing history.

    Example:

        response = raw_input(promptfmt("{style.blink.fg.red.bg.blue}GIMME INPUT:{style.none} "))

    """
    return string.format(
            style=_EscapeBuilderFactory(_Style, enableReadlineMarkers=True),
            cursor=_EscapeBuilderFactory(_Cursor, enableReadlineMarkers=True),
            scroll=_EscapeBuilderFactory(_Scroll, enableReadlineMarkers=True),
            clear=_EscapeBuilderFactory(_Clear, enableReadlineMarkers=True),
            *args,
            **kwargs
            )


def progress(string, *args, **kwargs):
    stdout("{resetColumn}{text}".format(
                resetColumn=cursor.col[0],
                text=string,
            ),
            suppressNewline=True,
            *args,
            **kwargs
            )


def done():
    stdout("{style.bold}Done{style.none}")


def statusANSI(color, text, termWidth=80, statusWidth=8, target=sys.stderr):
    text = text.center(statusWidth)
    startColumn = termWidth - len("[{}]".format(text))
    write("{startColumn}{style.fg.white}[{color}{text}{style.none.fg.white}]{style.none}",
            startColumn=cursor.col[startColumn],
            color=color,
            text=text,
            target=target,
            )


def statusOK(msg="OK", termWidth=80, statusWidth=8, target=sys.stderr):
    statusANSI(style.bold.fg.green, msg, termWidth, statusWidth, target=target)


def statusFail(msg="FAILED", termWidth=80, statusWidth=8, target=sys.stderr):
    statusANSI(style.bold.fg.red, msg, termWidth, statusWidth, target=target)


def statusDead(msg="DEAD", termWidth=80, statusWidth=8, target=sys.stderr):
    statusANSI(style.bold.fg.grey, msg, termWidth, statusWidth, target=target)


def debug(string, *args, **kwargs):
    kwargs.setdefault('target', sys.stderr)
    write("{style.bold.fg.grey}Debug:{style.none} " + string, *args, **kwargs)


def info(string, *args, **kwargs):
    kwargs.setdefault('target', sys.stderr)
    write("{style.bold.fg.cyan}Info:{style.none} " + string, *args, **kwargs)


def notice(string, *args, **kwargs):
    kwargs.setdefault('target', sys.stderr)
    write("{style.bold.fg.green}Notice:{style.none} " + string, *args, **kwargs)

notify = notice


def warning(string, *args, **kwargs):
    kwargs.setdefault('target', sys.stderr)
    write("{style.bold.fg.yellow}Warning:{style.none} " + string, *args, **kwargs)

warn = warning


def error(string, *args, **kwargs):
    kwargs.setdefault('target', sys.stderr)
    write("{style.bold.fg.red}Error:{style.none} " + string, *args, **kwargs)


def exception(exc, string=None, *args, **kwargs):
    kwargs.setdefault('target', sys.stderr)
    if string is None:
        write("{style.fg.black.bg.red}Caught Exception:{style.none} {exc}", exc=exc, *args, **kwargs)
    else:
        write("{style.fg.black.bg.red}Caught Exception:{style.none} {exc} " + string, exc=exc, *args, **kwargs)
    #TODO: Print traceback!


escapeRE = re.compile('\v\\[(?P<color_string>[a-zA-Z0-9_:; ]+)\\]')


def printa(string):
    """This function prints color-formatted strings.

    To add a color or attribute to a string, first add something of the
    following format:
        '\\v[f:red;b:blue;a:blink]'
    or:
        '\\v[s:reset]'

    printa("\\v[f:red;b:blue;a:blink]foo\\v[s:reset]")

    """
    warnings.warn("ansi.printa is deprecated in favor of ansi.write, ansi.stdout, or ansi.stderr!", DeprecationWarning)

    def subColor(matchobj):
        colorString = matchobj.group("color_string")
        colors = list()
        for directive in colorString.split(";"):
            cat, name = directive.split(":", 1)
            category = {
                    'a': Attributes,
                    'f': Foreground,
                    'b': Background,
                    's': Special,
            }[cat]
            val = getattr(category, name, None)
            if val is not None:
                colors.append(val)
            else:
                raise Exception("Unknown %s '%s'" % (category.__name__, name))

        return color(*colors)

    print(escapeRE.sub(subColor, string))


def cycleColors(text, colorCycle):
    colorCycle = itertools.cycle(colorCycle)
    return "".join("%s%s" % (next(colorCycle), letter) for letter in text) \
            + str(style.none)


nonPrintableRE = re.compile(
        '{ansiCSI}('
            '[0-9]*([{csiOneParamNoSpace}]| [{csiOneParamSpace}])|'
            '[0-9]*(;[0-9]*)*([{csiParamsNoSpace}]| [{csiParamsSpace}])'
            ')'.format(
        ansiCSI=ansiCSI.replace('[', r'\['),
        csiOneParamNoSpace='`@aAbBcCdDeEFGILMPSTUVXYZ',
        csiOneParamSpace='@CAE',
        csiParamsNoSpace='fHRghiJKlmnNoOQ',
        csiParamsSpace='DBFGH',
        ))


def countNonPrintable(text):
    total = 0

    for match in nonPrintableRE.finditer(text):
        total += match.end() - match.start()

    return total


def removeNonPrintable(text):
    return nonPrintableRE.sub('', text)


if __name__ == '__main__':
    # Printing a colored string.
    print(colorfmt("{style.blink.fg.red.bg.blue}BOOMWHACKERS!{style.none}"))

    # Demonstrating color cycles and the stdout and stderr convenience
    # functions.
    colorCycle = [getattr(style.fg, name) for name in [
            'red',
            'magenta',
            'blue',
            'cyan',
            'green',
            'yellow',
            ]]
    stdout("{coloredText} text on {style.bold}stdout{style.none}.",
            coloredText=cycleColors("Colored", colorCycle))
    stderr("{coloredText} text on {style.bold}stderr{style.none}.",
            coloredText=cycleColors("Colored", reversed(colorCycle)))

    # Progress notification:
    import time
    for idx in range(10):
        progress("Progress: {idx}/10... ", idx=idx)
        time.sleep(0.2)
    progress("Progress: {idx}/10... ", idx=10)
    done()

    # Output that roughly corresponds to some common logging levels:
    debug("Bugs. Hate 'em.")
    notice("Notice the moose.")
    warning("You're running the example!")
    error("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH!")
    exception(TypeError("This is what exceptions look like!"))

    # Status output, useful for init scripts and such:
    sys.stdout.write("Pork...")
    sys.stdout.flush()
    statusOK()
    sys.stdout.write("Bananas...")
    sys.stdout.flush()
    statusFail()
    sys.stdout.write("Bugs...")
    sys.stdout.flush()
    statusDead()

    # Getting a line from standard input with a colored prompt:
    #   Provide some fake history...
    import readline
    map(readline.add_history, [
            "Another history line.",
            "This is a really long history line that will probably screw up "
                "the output if you use raw_input. Try it out! Press 'up' "
                "until you get this line, then press 'down' again.",
            "A history line.",
            ])

    #   Create a nice thoroughly-colored prompt...
    prompt = '{style.fg.green}{filename}{style.bold.fg.black}:' \
            '{style.none.fg.green}{func} {style.bold.fg.green}=>{style.none} '

    #   Now, show the prompt and get the user's input...
    line = raw_input(promptfmt(prompt, filename=__file__, func='promptfmt'))
    stdout("Got input: {!r}", line)

    #   For comparison, get the user's input with the same prompt using
    #   raw_input instead...
    line = raw_input(colorfmt(prompt, filename=__file__, func='colorfmt'))
    stdout("Got input: {!r}", line)

    #####
    # The old, deprecated color API.
    print(color(Foreground.red, Background.blue, Attributes.blink)
            + "DEPRECATED!" + color())
