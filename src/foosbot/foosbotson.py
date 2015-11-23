from requests import exceptions
from slacker import Slacker
import challonge

import logging
logger = logging.getLogger("foosbotson")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('foosbotson.log')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

class FoosBotson:

    group_stage_id_map = None

    def __init__(self,
                 challonge_tournament_name,
                 api_token='xoxb-15050499792-qRGSf7w5Qv0Eitp7XMoC8w39',
                 slack_username="Foo Botson",
                 slack_icon_url='http://i.imgur.com/GlnLNWg.jpg',
                 challonge_api_key='ubxCn7J3myaGWsYLeFliIIFD53HhUJQZdgUOlEvY',
                 challonge_username='nlafarge'):

        self.logger = logging.getLogger('foosbotson.FoosBotson')

        self.slack = Slacker(api_token)
        self.slack_default_username = slack_username
        self.slack_default_icon_url = slack_icon_url
        self.nick_slack_id = 'U0EFNV9SN'

        self.challonge_tournament_name = challonge_tournament_name
        self.tournament_name = 'amadeus-%s' % challonge_tournament_name
        self.logger.info("Connecting to tournament with id %s" % self.tournament_name)

        challonge.set_credentials(challonge_username, challonge_api_key)
        self.tournament = challonge.tournaments.show(self.tournament_name)
        self.participants = challonge.participants.index(self.tournament_name)
        self.matches = challonge.matches.index(self.tournament_name)

        self.find_group_stage_ids()

    def find_group_stage_ids(self):
        from bs4 import BeautifulSoup
        import urllib2
        import urlparse
        url = urlparse.urljoin('http://amadeus.challonge.com/', self.challonge_tournament_name)
        soup = BeautifulSoup(urllib2.urlopen(url).read())
        participant_id_map = {p['display-name']: p['id'] for p in self.participants}
        self.group_stage_id_map = {int(r['data-participant_id']): participant_id_map[r.get_text()] for r in
                                   soup.find_all('div', {'class': 'inner_content'})}

    def check_match_results(self):
        matches = challonge.matches.index(self.tournament_name)

        new_match_results = [m['winner-id'] for m in matches]
        old_match_results = [m['winner-id'] for m in self.matches]

        if new_match_results != old_match_results:
            # These will differ when we enter the next stage of the tournament
            if len(new_match_results) == len(old_match_results):
                self.logger.debug("New Match Results Received")
                self.logger.debug("Old Results" + str(old_match_results))
                self.logger.debug("New Results" + str(new_match_results))
                for i in range(len(matches)):
                    new_winner = matches[i]['winner-id']
                    old_winner = self.matches[i]['winner-id']
                    if new_winner and new_winner != old_winner:
                        winner_id = matches[i]['winner-id']
                        loser_id = matches[i]['loser-id']

                        # For the group stage hack to work
                        if winner_id < 30000000 and loser_id < 30000000:
                            # Reload the map (this can happen if a stage is reset, new group ids are generated)
                            if not self.group_stage_id_map or winner_id not in self.group_stage_id_map:
                                self.find_group_stage_ids()

                            winner_id = self.group_stage_id_map[winner_id]
                            loser_id = self.group_stage_id_map[loser_id]

                        winner_name = challonge.participants.show(self.tournament_name, winner_id)['display-name']
                        loser_name = challonge.participants.show(self.tournament_name, loser_id)['display-name']

                        ordered_scores = sorted(matches[i]['scores-csv'].split('-'), key=int, reverse=True)

                        round_number = matches[i]['round']
                        if matches[i]['group-id']:
                            msg = ":foosball: *%s* has defeated *%s* by a score of `%s` :darthfoosball:" % (
                                winner_name, loser_name, '-'.join(ordered_scores)
                            )
                        elif round_number == 1:
                            msg = ":foosball: *%s* has defeated *%s* by a score of `%s` to " \
                                  "advance to the finals :darthfoosball:" % (
                                winner_name, loser_name, '-'.join(ordered_scores)
                            )
                        elif round_number == 2:
                            self.post_direct_message(":foosball: :foosball: WE HAVE NEW FOOSBALL CHAMPIONS!!"
                                                     " :foosball: :foosball:")
                            msg = ":darthfoosball: :darthfoosball: Congrats to *%s* for defeating *%s* by a score " \
                                  "of `%s` :darthfoosball: :darthfoosball:" % (
                                winner_name, loser_name, '-'.join(ordered_scores)
                            )
                        else:
                            self.logger.error("Unexpected Round Number: %i" % round_number)
                        self.post_direct_message(msg)
                        self.logger.info(msg)

            self.matches = matches

    def add_reaction_to_all_in_channel(self, channel, reaction):
        resp = self.slack.channels.history(channel)
        for message in resp.body['messages']:
            self.add_reaction_to_message(message, channel, reaction)

    def add_reaction_to_message(self, message, channel, reaction):
        reactions_list = self.slack.reactions.get(channel=channel, timestamp=message['ts'], full=True)
        message = reactions_list.body['message']
        reaction_names = {}
        if 'reactions' in message:
            reaction_names = [r['name'] for r in message['reactions']]
        if reaction not in reaction_names:
            self.slack.reactions.add(reaction, channel=channel, timestamp=message['ts'])

    def post_message_to_chat(self, channel, message, username=None, icon=None):

        if not username:
            username = self.slack_default_username

        if not icon:
            icon = self.slack_default_icon_url

        try:
            self.slack.chat.post_message(channel,
                                         message,
                                         username=username,
                                         icon_url=icon,
                                         link_names=1)
        except exceptions.HTTPError as e:
            self.logger.error(e)

    def post_message_to_chat_channel(self, slack_channel, message, username=None, icon=None):
        if not username:
            username = self.slack_default_username

        if not icon:
            icon = self.slack_default_icon_url

        self.post_message_to_chat(slack_channel, message, username=username, icon=icon)

    def post_direct_message(self, message, user_id=None, username=None, icon=None):
        if not username:
            username = self.slack_default_username

        if not icon:
            icon = self.slack_default_icon_url

        if not user_id:
            user_id = self.nick_slack_id

        try:
            response = self.slack.im.open(user=user_id)
            channel_id = response.body['channel']['id']
            self.post_message_to_chat(channel_id, message, username=username, icon=icon)
        except exceptions.RequestException as e:
            self.logger.error(e)


if __name__ == '__main__':
    foosbot = FoosBotson('bottesting')

    import schedule
    import time

    schedule.every(5).minutes.do(foosbot.check_match_results)  # TODO tweak interval

    while True:
        schedule.run_pending()
        time.sleep(1)
