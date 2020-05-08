from redbot.core import commands
import os
import sys
import dotenv
from .ir_webstats_rc.client import iRWebStats
from .ir_webstats_rc.constants import IRATING_DIRT_OVAL_CHART, IRATING_ROAD_CHART, IRATING_OVAL_CHART, IRATING_DIRT_ROAD_CHART
from .ir_webstats_rc.responses.last_races_stats import LastRacesStats
from .ir_webstats_rc.responses.yearly_stats import YearlyStats
from .ir_webstats_rc.responses.career_stats import CareerStats
from .storage import *
import copy
import discord

dotenv.load_dotenv()

irw = iRWebStats()
irw.login(os.getenv("IRACING_USERNAME"), os.getenv("IRACING_PASSWORD"))

all_series = irw.all_seasons()


class Iracing(commands.Cog):
    """A cog that can give iRacing data about users"""

    @commands.command()
    async def recentraces(self, ctx, *, iracing_id=None):
        """Gives the recent race data from the iRacing ID passed in"""
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        if not iracing_id:
            iracing_id = get_user_iracing_id(user_id, guild_id)
            if not iracing_id:
                await ctx.send('Please send an iRacing ID after the command or link your own with `!saveid <iRacing '
                               'ID>`')
                return

        races_stats_list = update_last_races(user_id, guild_id, iracing_id)

        await ctx.send(print_recent_races(races_stats_list, iracing_id))

    @commands.command()
    async def yearlystats(self, ctx, *, iracing_id=None):
        """Gives the yearly data from the iRacing ID passed in"""
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        if not iracing_id:
            iracing_id = get_user_iracing_id(user_id, guild_id)
            if not iracing_id:
                await ctx.send('Please send an iRacing ID after the command or link your own with `!saveid <iRacing '
                               'ID>`')
                return

        yearly_stats = update_yearly_stats(user_id, guild_id, iracing_id)

        await ctx.send(print_yearly_stats(yearly_stats, iracing_id))

    @commands.command()
    async def careerstats(self, ctx, *, iracing_id=None):
        """Gives the career data from the iRacing ID passed in"""
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        if not iracing_id:
            iracing_id = get_user_iracing_id(user_id, guild_id)
            if not iracing_id:
                await ctx.send('Please send an iRacing ID after the command or link your own with `!saveid <iRacing '
                               'ID>`')
                return

        career_stats = update_career_stats(user_id, guild_id, iracing_id)

        update_user(user_id, guild_id, copy.deepcopy(career_stats), None, None)

        await ctx.send(print_career_stats(career_stats, iracing_id))

    @commands.command()
    async def saveid(self, ctx, *, iracing_id):
        """Save your iRacing ID with to your Discord ID"""
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)

        save_iracing_id(user_id, guild_id, iracing_id)
        await ctx.send('iRacing ID successfully saved')

    @commands.command()
    async def leaderboard(self, ctx, category='road'):
        """Displays a leaderboard of the users who have used `!saveid`.
        If the data is not up to date, try `!update` first.
        The categories are `road`, `oval`, `dirtroad`, and `dirtoval`"""
        if category not in ['road', 'oval', 'dirtroad', 'dirtoval']:
            await ctx.send('Please try again with one of these categories: `road`, `oval`, `dirtroad`, `dirtoval`')
            return

        guild_dict = get_dict_of_data(ctx.guild.id)
        if category == 'road':
            sorted_list = sorted(guild_dict.items(), key=lambda x: x[1]['road_irating'], reverse=True)
            await ctx.send(print_leaderboard(sorted_list, ctx.guild, category))
        elif category == 'oval':
            sorted_list = sorted(guild_dict.items(), key=lambda x: x[1]['oval_irating'], reverse=True)
            await ctx.send(print_leaderboard(sorted_list, ctx.guild, category))
        elif category == 'dirtroad':
            sorted_list = sorted(guild_dict.items(), key=lambda x: x[1]['dirt_road_irating'], reverse=True)
            await ctx.send(print_leaderboard(sorted_list, ctx.guild, category))
        elif category == 'dirtoval':
            sorted_list = sorted(guild_dict.items(), key=lambda x: x[1]['dirt_oval_irating'], reverse=True)
            await ctx.send(print_leaderboard(sorted_list, ctx.guild, category))

    @commands.command()
    async def update(self, ctx):
        guild_id = ctx.guild.id
        guild_dict = get_dict_of_data(guild_id)
        for user_id in guild_dict:
            if 'iracing_id' in guild_dict[user_id]:
                update_user_data(user_id, guild_id, (guild_dict[user_id]['iracing_id']))

        await ctx.send('Successfully updated user data')


def print_leaderboard(user_data_list, guild, category):
    string = 'iRacing ' + lowercase_to_readable_categories(category) + ' Leaderboard' + '\n\n'
    string += 'Racer'.ljust(16) + \
              'Starts'.ljust(8) + \
              'iRating'.ljust(16) + \
              'Wins'.ljust(8) + \
              'Top 5s'.ljust(8) + \
              'Win %'.ljust(9) + \
              'Top 5 %'.ljust(9) + \
              'Avg Start'.ljust(12) + \
              'Avg Finish'.ljust(12) + \
              'Avg Incidents'.ljust(15) + '\n'
    string += '----------------------------------------------------------------------------------------------------' \
              '-----------\n'

    for item in user_data_list:
        member = discord.utils.find(lambda m: m.id == int(item[0]), guild.members)
        career_stats_list = list(map(lambda x: CareerStats(x), item[-1]['career_stats']))

        irating = 0
        if category == 'road':
            irating = item[-1]['road_irating']
        elif category == 'oval':
            irating = item[-1]['oval_irating']
        elif category == 'dirtroad':
            irating = item[-1]['dirt_road_irating']
        elif category == 'dirtoval':
            irating = item[-1]['dirt_oval_irating']

        career_stats = None
        for career_stat in career_stats_list:
            if category == 'road':
                if career_stat.category == 'Road':
                    career_stats = career_stat
            elif category == 'oval':
                if career_stat.category == 'Oval':
                    career_stats = career_stat
            elif category == 'dirtroad':
                if career_stat.category == 'Dirt+Road':
                    career_stats = career_stat
            elif category == 'dirtoval':
                if career_stat.category == 'Dirt+Oval':
                    career_stats = career_stat

        if career_stats:
            string += member.name.ljust(16) + \
                      str(career_stats.starts).ljust(8) + \
                      str(irating).ljust(16) + \
                      str(career_stats.wins).ljust(8) + \
                      str(career_stats.top5).ljust(8) + \
                      str(career_stats.winPerc).ljust(9) + \
                      str(career_stats.top5Perc).ljust(9) + \
                      str(career_stats.avgStart).ljust(12) + \
                      str(career_stats.avgFinish).ljust(12) + \
                      str(career_stats.avgIncPerRace).ljust(15) + '\n'

    return add_backticks(string)


def lowercase_to_readable_categories(category):
    if category == 'road':
        return 'Road'
    elif category == 'oval':
        return 'Oval'
    elif category == 'dirtroad':
        return 'Dirt Road'
    elif category == 'dirtoval':
        return 'Dirt Oval'


def save_iratings(user_id, guild_id):
    iracing_id = get_user_iracing_id(user_id, guild_id)

    oval_irating = get_irating(iracing_id, IRATING_OVAL_CHART)
    road_irating = get_irating(iracing_id, IRATING_ROAD_CHART)
    dirt_oval_irating = get_irating(iracing_id, IRATING_DIRT_OVAL_CHART)
    dirt_road_irating = get_irating(iracing_id, IRATING_DIRT_ROAD_CHART)

    irating_dict = {
        IRATING_OVAL_CHART: oval_irating,
        IRATING_ROAD_CHART: road_irating,
        IRATING_DIRT_OVAL_CHART: dirt_oval_irating,
        IRATING_DIRT_ROAD_CHART: dirt_road_irating
    }

    save_irating(user_id, guild_id, irating_dict)


def update_user_data(user_id, guild_id, iracing_id):
    update_last_races(user_id, guild_id, iracing_id)
    update_yearly_stats(user_id, guild_id, iracing_id)
    update_career_stats(user_id, guild_id, iracing_id)
    save_iratings(user_id, guild_id)


def update_last_races(user_id, guild_id, iracing_id):
    races_stats_dict = irw.lastrace_stats(iracing_id)
    if races_stats_dict:
        races_stats_list = map(lambda x: LastRacesStats(x), races_stats_dict)
        update_user(user_id, guild_id, None, None, copy.deepcopy(races_stats_list))
        return races_stats_list


def update_yearly_stats(user_id, guild_id, iracing_id):
    yearly_stats_dict = irw.yearly_stats(iracing_id)
    if yearly_stats_dict:
        yearly_stats_list = map(lambda x: YearlyStats(x), yearly_stats_dict)
        update_user(user_id, guild_id, None, copy.deepcopy(yearly_stats_list), None)
        return yearly_stats_list


def update_career_stats(user_id, guild_id, iracing_id):
    career_stats_dict = irw.career_stats(iracing_id)
    if career_stats_dict:
        career_stats_list = map(lambda x: CareerStats(x), career_stats_dict)
        update_user(user_id, guild_id, copy.deepcopy(career_stats_list), None, None)
        return career_stats_list


def get_irating(user_id, category):
    chart = irw.iratingchart(user_id, category)
    if not isinstance(chart, list) or not isinstance(chart[-1], list):
        return None
    return str(chart[-1][-1])


def get_series_name(series_id):
    for series in all_series:
        if series.seriesId == series_id:
            return series.name

    return ""


def print_career_stats(career_stats, iracing_id):
    string = 'Career Data for user: ' + str(iracing_id) + '\n\n'
    string += 'Category'.ljust(10) + \
              'Starts'.ljust(8) + \
              'Top 5s'.ljust(8) + \
              'Wins'.ljust(8) + \
              'Avg Start'.ljust(12) + \
              'Avg Finish'.ljust(12) + \
              'Avg Incidents'.ljust(15) + \
              'Top 5 %'.ljust(9) + \
              'Win %'.ljust(8) + '\n'
    string += '--------------------------------------------------------------------' \
              '---------------------\n'

    for career_stat in career_stats:
        string += career_stat.category.ljust(10) + \
                  str(career_stat.starts).ljust(8) + \
                  str(career_stat.top5).ljust(8) + \
                  str(career_stat.wins).ljust(8) + \
                  str(career_stat.avgStart).ljust(12) + \
                  str(career_stat.avgFinish).ljust(12) + \
                  str(career_stat.avgIncPerRace).ljust(15) + \
                  str(career_stat.top5Perc).ljust(9) + \
                  str(career_stat.winPerc).ljust(8) + '\n'

    return add_backticks(string)


def print_yearly_stats(yearly_stats, iracing_id):
    string = 'Yearly Data for user: ' + str(iracing_id) + '\n\n'
    string += 'Year'.ljust(6) + \
              'Category'.ljust(10) + \
              'Starts'.ljust(8) + \
              'Top 5s'.ljust(8) + \
              'Wins'.ljust(8) + \
              'Avg Start'.ljust(12) + \
              'Avg Finish'.ljust(12) + \
              'Avg Incidents'.ljust(15) + \
              'Top 5 %'.ljust(9) + \
              'Win %'.ljust(7) + '\n'
    string += '--------------------------------------------------------------------' \
              '---------------------------\n'

    for yearly_stat in yearly_stats:
        string += str(yearly_stat.year).ljust(6) + \
                  yearly_stat.category.ljust(10) + \
                  str(yearly_stat.starts).ljust(8) + \
                  str(yearly_stat.top5).ljust(8) + \
                  str(yearly_stat.wins).ljust(8) + \
                  str(yearly_stat.avgStart).ljust(12) + \
                  str(yearly_stat.avgFinish).ljust(12) + \
                  str(yearly_stat.avgIncPerRace).ljust(15) + \
                  str(yearly_stat.top5Perc).ljust(9) + \
                  str(yearly_stat.winPerc).ljust(7) + '\n'

    return add_backticks(string)


def print_recent_races(recent_races, iracing_id):
    string = 'Recent Races Data for user: ' + str(iracing_id) + '\n\n'
    string += 'Finish'.ljust(8) + \
              'Start'.ljust(8) + \
              'Incidents'.ljust(11) + \
              'Avg iRating'.ljust(13) + \
              'Race Date'.ljust(15) + \
              'Series'.ljust(38) + \
              'Track Name'.ljust(30) + '\n'
    string += '------------------------------------------------------------------------------------' \
              '-----------------------\n'

    for recent_race in recent_races:
        string += ('P' + str(recent_race.finishPos)).ljust(8) + \
                  ('P' + str(recent_race.startPos)).ljust(8) + \
                  str(recent_race.incidents).ljust(11) + \
                  str(recent_race.sof).ljust(13) + \
                  recent_race.date.ljust(15) + \
                  get_series_name(recent_race.seriesID).ljust(38) + \
                  recent_race.trackName.ljust(30) + '\n'

    return add_backticks(string)


def add_backticks(string):
    return '```' + string + '```'
