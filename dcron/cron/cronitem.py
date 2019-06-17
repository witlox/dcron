#!/usr/bin/env python
# -*- coding: utf-8 -*-#

# MIT License
#
# Copyright (c) 2019 Pim Witlox
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import re

from datetime import datetime, time, date

from dcron.cron.utils import items_regex, special_regex, S_INFO, SPECIALS, SPECIAL_IGNORE
from dcron.cron.orderedvariablelist import OrderedVariableList


class CronItem(object):
    """
    An item which objectifies a single line of a CronTab and may be considered to be a cron job object.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, command='', comment='', user=None, cron=None):
        self.cron = cron
        self.user = user
        self.valid = False
        self.enabled = True
        self.special = False
        self.comment = None
        self.command = None
        self.last_run = None
        self.assigned_to = None
        self.pid = None
        self.remove = False
        self.env = OrderedVariableList(job=self)
        self.marker = None
        self.pre_comment = False
        self._log = []
        self.parts = CronDateTimeParts()
        self.set_comment(comment)
        if command:
            self.set_command(command)
            self.valid = True

    @classmethod
    def from_line(cls, line, user=None, cron=None):
        """
        Generate CronItem from a cron-line and parse out command and comment
        """
        obj = cls(user=user, cron=cron)
        obj.parse(line.strip())
        return obj

    def delete(self):
        """
        Delete this item and remove it from it's parent
        """
        if not self.cron:
            raise UnboundLocalError("Cron item is not in a crontab!")
        else:
            self.cron.remove(self)

    def set_command(self, cmd):
        """
        Set the command and filter as needed
        """
        self.command = cmd.strip()

    def set_comment(self, cmt):
        """
        Set the comment and don't filter
        """
        if cmt and cmt[:8] == 'Ansible:':
            self.marker = 'Ansible'
            self.pre_comment = True
            self.comment = cmt[8:].lstrip()
        else:
            self.comment = cmt

    def parse(self, line):
        """
        Parse a cron line string and save the info as the objects.
        """
        if not line or line[0] == '#':
            self.enabled = False
            line = line[1:].strip()
        # We parse all lines so we can detect disabled entries.
        self._set_parse(items_regex.findall(line))
        self._set_parse(special_regex.findall(line))

    def _set_parse(self, result):
        """
        Set all the parsed variables into the item
        """
        if not result:
            return
        self.comment = result[0][-1]
        if self.cron.user is False:
            # Special flag to look for per-command user
            ret = result[0][-3].split(None, 1)
            self.set_command(ret[-1])
            if len(ret) == 2:
                self.user = ret[0]
            else:
                self.valid = False
                self.enabled = False
                self.logger.error("Missing user or command in system cron line.")
        else:
            self.set_command(result[0][-3])
        try:
            self.set_all(*result[0][:-3])
            self.valid = True
        except (ValueError, KeyError) as err:
            if self.enabled:
                self.logger.error(err)
            self.valid = False
            self.enabled = False

    def enable(self, enabled=True):
        """
        Set if this cron job is enabled or not
        """
        if enabled in [True, False]:
            self.enabled = enabled
        return self.enabled

    def is_enabled(self):
        """
        Return true if this job is enabled (not commented out)
        """
        return self.enabled

    def is_valid(self):
        """
        Return true if this job is valid
        """
        return self.valid

    def every_reboot(self):
        """
        Set to every reboot instead of a time pattern: @reboot
        """
        self.clear()
        return self.parts.set_all('@reboot')

    def every(self, unit=1):
        """
        Replace existing time pattern with a single unit, setting all lower
        units to first value in valid range.

        For instance job.every(3).days() will be `0 0 */3 * *`
        while job.day().every(3) would be `* * */3 * *`

        Many of these patterns exist as special tokens on Linux, such as
        `@midnight` and `@hourly`
        """
        return Every(self.parts, unit)

    def set_all(self, *args):
        """
        Replace existing time pattern with these five values given as args:
           job.setall("1 2 * * *")
           job.setall(1, 2) == '1 2 * * *'
           job.setall(0, 0, None, '>', 'SUN') == '0 0 * 12 SUN'
        """
        return self.parts.set_all(*args)

    def clear(self):
        """
        Clear the special and set values
        """
        return self.parts.clear()

    def frequency(self, year=None):
        """
        Returns the number of times this item will execute in a given year (defaults to this year)
        """
        return self.parts.frequency(year=year)

    def frequency_per_year(self, year=None):
        """
        Returns the number of /days/ this item will execute on in a year (defaults to this year)
        """
        return self.parts.frequency_per_year(year=year)

    def frequency_per_day(self):
        """
        Returns the number of time this item will execute in any day
        """
        return self.parts.frequency_per_day()

    def frequency_per_hour(self):
        """
        Returns the number of times this item will execute in any hour
        """
        return self.parts.frequency_per_hour()

    def append_log(self, line):
        self._log.append(line)

    @property
    def log(self):
        """
        Return a cron log specific for this job only
        """
        result = self._log
        try:
            with open('/var/log/syslog', 'r') as syslog:
                match = re.match(
                    r'(?P<date>\w+ +\d+ +\d\d:\d\d:\d\d) (?P<host>\w+) CRON\[(?P<pid>\d+)\]: \((?P<user>\w+)\) CMD \((?P<cmd>.*)\)',
                    syslog.readline())
                data = match and match.groupdict()
                if data and (not self.user or data['user'] == self.user):
                    result.append(data)
        except FileNotFoundError:
            pass
        return result

    @property
    def minute(self):
        """
        Return the minute part
        """
        return self.parts[0]

    @property
    def minutes(self):
        """
        Same as minute
        """
        return self.minute

    @property
    def hour(self):
        """
        Return the hour part
        """
        return self.parts[1]

    @property
    def hours(self):
        """
        Same as hour
        """
        return self.hour

    @property
    def day(self):
        """
        Return the day part
        """
        return self.dom

    @property
    def dom(self):
        """
        Return the day-of-the month part
        """
        return self.parts[2]

    @property
    def month(self):
        """
        Return the month part
        """
        return self.parts[3]

    @property
    def months(self):
        """
        Same as month
        """
        return self.month

    @property
    def dow(self):
        """
        Return the day of the week part
        """
        return self.parts[4]

    def __len__(self):
        return len(str(self))

    def __getitem__(self, key):
        return self.parts[key]

    def __eq__(self, other):
        if other and (isinstance(other, CronItem)):
            return self.command == other.command and self.minute == other.minute and self.hour == other.hour and \
                   self.month == other.month and self.dow == other.dow and self.dom == other.dom
        return False

    def __lt__(self, value):
        return self.frequency() < CronDateTimeParts(value).frequency()

    def __gt__(self, value):
        return self.frequency() > CronDateTimeParts(value).frequency()

    def __str__(self):
        if not self.is_valid() and self.enabled:
            raise ValueError('Refusing invalid CronTab. Disable to continue.')
        user = ''
        if self.cron and self.cron.user is False:
            if not self.user:
                raise ValueError("Job to system-cron format, no user set!")
            user = self.user + ' '
        result = "{0} {1}{2}".format(str(self.parts), user, self.command)
        if self.comment:
            comment = self.comment
            if self.marker:
                comment = "#{0}: {1}".format(self.marker, comment)
            else:
                comment = "# " + comment

            if self.pre_comment:
                result = comment + "\n" + result
            else:
                result += ' ' + comment

        if not self.enabled:
            result = "# " + result
        if self.assigned_to:
            result += "assigned to {0}".format(self.assigned_to)
        return str(self.env) + result


class CronDateTimeParts(list):
    """
    Controls a list of five time parts which represent:
        minute frequency, hour frequency, day of month frequency,
        month frequency and finally day of the week frequency.
    """

    def __init__(self, *args):
        super(CronDateTimeParts, self).__init__([CronDateTimePart(info) for info in S_INFO])
        self.special = None
        self.set_all(*args)
        self.is_valid = self.is_self_valid

    def is_self_valid(self, *args):
        """
        Object version of is_valid
        """
        return CronDateTimeParts.is_valid(*(args or (self,)))

    @classmethod
    def is_valid(cls, *args):
        """
        Returns true if the arguments are valid cron pattern
        """
        try:
            return bool(cls(*args))
        except (ValueError, KeyError):
            return False

    def set_all(self, *parts):
        """
        Parses the various ways date/time frequency can be specified
        """
        self.clear()
        if len(parts) == 1:
            (parts, self.special) = self._parse_value(parts[0])
            if parts[0] == '@reboot':
                return
        if id(parts) == id(self):
            raise AssertionError("Can not set cron to itself!")
        for set_a, set_b in zip(self, parts):
            set_a.parse(set_b)

    @staticmethod
    def _parse_value(value):
        """
        Parse a single value into an array of parts
        """
        if isinstance(value, str) and value:
            return CronDateTimeParts._parse_str(value)
        if isinstance(value, CronItem):
            return value.parts, None
        elif isinstance(value, datetime):
            return [value.minute, value.hour, value.day, value.month, '*'], None
        elif isinstance(value, time):
            return [value.minute, value.hour, '*', '*', '*'], None
        elif isinstance(value, date):
            return [0, 0, value.day, value.month, '*'], None
            # It might be possible to later understand timedelta objects
            # but there's no convincing mathematics to do the conversion yet.
        elif not isinstance(value, (list, tuple)):
            raise ValueError("Unknown type: {}".format(type(value).__name__))
        return value, None

    @staticmethod
    def _parse_str(value):
        """
        Parse a string which contains part information
        """
        key = value.lstrip('@').lower()
        if value.count(' ') == 4:
            return value.strip().split(' '), None
        elif key in SPECIALS.keys():
                return SPECIALS[key].split(' '), '@' + key
        elif value.startswith('@'):
            raise ValueError("Unknown special '{}'".format(value))
        return [value], None

    def clear(self):
        """
        Clear the special and set values
        """
        self.special = None
        for item in self:
            item.clear()

    def frequency(self, year=None):
        """
        Return frequency per year times frequency per day
        """
        return self.frequency_per_year(year=year) * self.frequency_per_day()

    def frequency_per_year(self, year=None):
        """
        Returns the number of times this item will execute in a given year (default is this year)
        """
        result = 0
        if not year:
            year = date.today().year

        weekdays = list(self[4])

        for month in self[3]:
            for day in self[2]:
                try:
                    if date(year, month, day).weekday() in weekdays:
                        result += 1
                except ValueError:
                    continue
        return result

    def frequency_per_day(self):
        """
        Returns the number of times this item will execute in any day
        """
        return len(self[0]) * len(self[1])

    def frequency_per_hour(self):
        """
        Returns the number of times this item will execute in any hour
        """
        return len(self[0])

    def __str__(self):
        parts = ' '.join([str(s) for s in self])
        if self.special:
            if self.special == '@reboot' or SPECIALS[self.special.strip('@')] == parts:
                return self.special
        for (name, value) in SPECIALS.items():
            if value == parts and name not in SPECIAL_IGNORE:
                return "@{0}".format(name)
        return parts

    def __eq__(self, arg):
        return str(self) == str(CronDateTimeParts(arg))


class CronDateTimePart(object):
    """
    Cron part object which shows a time pattern
    """

    def __init__(self, info, value=None):
        if isinstance(info, int):
            info = S_INFO[info]
        self.min = info.get('min', None)
        self.max = info.get('max', None)
        self.name = info.get('name', None)
        self.enum = info.get('enum', None)
        self.parts = []
        if value:
            self.parse(value)

    def parse(self, value):
        """
        Set values into the part.
        """
        self.clear()
        if value is not None:
            for part in str(value).split(','):
                if part.find("/") > 0 or part.find("-") > 0 or part == '*':
                    self.parts += self.get_range(part)
                    continue
                self.parts.append(self.parse_value(part, sunday=0))

    def __eq__(self, value):
        return str(self) == str(value)

    def __str__(self):
        if not self.parts:
            return '*'
        return _render_values(self.parts, ',')

    def every(self, n_value, also=False):
        """
        Set the every X units value
        """
        if not also:
            self.clear()
        self.parts += self.get_range(int(n_value))
        return self.parts[-1]

    def on(self, *n_value, **opts):
        """
        Set the time values to the specified placements.
        """
        if not opts.get('also', False):
            self.clear()
        for set_a in n_value:
            self.parts += self.parse_value(set_a, sunday=0),
        return self.parts

    def during(self, vfrom, vto, also=False):
        """
        Set the During value, which sets a range
        """
        if not also:
            self.clear()
        self.parts += self.get_range(str(vfrom) + '-' + str(vto))
        return self.parts[-1]

    @property
    def also(self):
        """
        Appends rather than replaces the new values
        """
        return Also(self)

    def clear(self):
        """
        clear the part ready for new values
        """
        self.parts = []

    def get_range(self, *vrange):
        """
        Return a cron range for this part
        """
        ret = CronRange(self, *vrange)
        if ret.dangling is not None:
            return [ret.dangling, ret]
        return [ret]

    def __iter__(self):
        """
        Return the entire element as an iterable
        """
        ret = {}
        # An empty part means '*' which is every(1)
        if not self.parts:
            self.every(1)
        for part in self.parts:
            if isinstance(part, CronRange):
                for bit in part.range():
                    ret[bit] = 1
            else:
                ret[int(part)] = 1
        for val in ret:
            yield val

    def __len__(self):
        """
        Returns the number of times this part happens in it's range
        """
        return len(list(self.__iter__()))

    def parse_value(self, val, sunday=None):
        """
        Parse the value of the cron part and raise any errors needed
        """
        if val == '>':
            val = self.max
        elif val == '<':
            val = self.min
        try:
            out = self._get_cron_value(val, self.enum)
        except ValueError:
            raise ValueError("Unrecognised {0}: '{1}'".format(self.name, val))
        except KeyError:
            raise KeyError("No enumeration for {0}: '{1}'".format(self.name, val))

        if self.max == 6 and int(out) == 7:
            if sunday is not None:
                return sunday

        if int(out) < self.min or int(out) > self.max:
            raise ValueError("'{1}', not in {0.min}-{0.max} for {0.name}".format(self, val))
        return out

    @staticmethod
    def _get_cron_value(value, enums):
        """
        Returns a value as int (pass-through) or a special enum value
        """
        if isinstance(value, int):
            return value
        elif str(value).isdigit():
            return int(str(value))
        if not enums:
            raise KeyError("No enumeration allowed")
        return CronValue(str(value), enums)


class Every(object):
    """
    Provide an interface to the job.every() method:
       Available Calls:
          minute, minutes, hour, hours, dom, doms, month, months, dow, dows

       Once run all units will be cleared (set to *) then proceeding units
       will be set to '0' and the target unit will be set as every x units.
    """

    def __init__(self, item, units):
        self.parts = item
        self.unit = units
        for (key, name) in enumerate(['minute', 'hour', 'dom', 'month', 'dow', 'min', 'hour', 'day', 'moon', 'weekday']):
            setattr(self, name, self.set_attr(key % 5))
            setattr(self, name+'s', self.set_attr(key % 5))

    def set_attr(self, target):
        """
        Inner set target, returns function
        """
        def inner():
            """
            Returned inner call for setting part targets
            """
            self.parts.clear()
            # Day-of-week is actually a level 2 set, not level 4.
            for key in range(target == 4 and 2 or target):
                self.parts[key].on('<')
            self.parts[target].every(self.unit)
        return inner

    def year(self):
        """
        Special every year target
        """
        if self.unit > 1:
            raise ValueError("Invalid value '%s', outside 1 year" % self.unit)
        self.parts.set_all('@yearly')


class Also(object):
    """
    Link range values together (appending instead of replacing)
    """

    def __init__(self, obj):
        self.obj = obj

    def every(self, *a):
        """
        Also every one of these
        """
        return self.obj.every(*a, also=True)

    def on(self, *a):
        """
        Also on these
        """
        return self.obj.on(*a, also=True)

    def during(self, *a):
        """
        Also during these
        """
        return self.obj.during(*a, also=True)


class CronValue(object):
    """
    Represent a special value in the cron line
    """

    def __init__(self, value, enums):
        self.text = value
        self.value = enums.index(value.lower())

    def __lt__(self, value):
        return self.value < int(value)

    def __str__(self):
        return self.text

    def __int__(self):
        return self.value


class CronRange(object):
    """
    A range between one value and another for a time range.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, vpart, *vrange):
        # holds an extra dangling entry, for example sundays.
        self.dangling = None
        self.part = vpart
        self.cron = None
        self.seq = 1

        if not vrange:
            self.all()
        elif isinstance(vrange[0], str):
            self.parse(vrange[0])
        elif isinstance(vrange[0], (int, CronValue)):
            if len(vrange) == 2:
                (self.vfrom, self.vto) = vrange
            else:
                self.seq = vrange[0]
                self.all()

    def parse(self, value):
        """
        Parse a ranged value in a cronjob
        """
        if value.count('/') == 1:
            value, seq = value.split('/')
            self.seq = self.part.parse_value(seq)
            if self.seq < 1 or self.seq > self.part.max:
                raise ValueError("Sequence can not be divided by zero or max")
        if value.count('-') == 1:
            vfrom, vto = value.split('-')
            self.vfrom = self.part.parse_value(vfrom, sunday=0)
            self.vto = self.part.parse_value(vto)
            if self.vto < self.vfrom:
                self.logger.warning("Bad range '{0.vfrom}-{0.vto}'".format(self))
        elif value == '*':
            self.all()
        else:
            raise ValueError('Unknown cron range value "%s"' % value)

    def all(self):
        """
        Set this part to all units between the minimum and maximum
        """
        self.vfrom = self.part.min
        self.vto = self.part.max

    def range(self):
        """
        Returns the range of this cron part as a iterable list
        """
        return range(int(self.vfrom), int(self.vto)+1, self.seq)

    def every(self, value):
        """
        Set the sequence value for this range.
        """
        self.seq = int(value)

    def __lt__(self, value):
        return int(self.vfrom) < int(value)

    def __gt__(self, value):
        return int(self.vto) > int(value)

    def __int__(self):
        return int(self.vfrom)

    def __str__(self):
        value = '*'
        if int(self.vfrom) > self.part.min or int(self.vto) < self.part.max:
            if self.vfrom == self.vto:
                value = str(self.vfrom)
            else:
                value = _render_values([self.vfrom, self.vto], '-')
        if self.seq != 1:
            value += "/{0}".format(self.seq)
        if value != '*':
            value = ','.join([str(val) for val in self.range()])
        return value


def _render_values(values, sep=','):
    """
    Returns a rendered list, sorted and optionally resolved
    """
    if len(values) > 1:
        values.sort()
    return sep.join([str(val) for val in values])
