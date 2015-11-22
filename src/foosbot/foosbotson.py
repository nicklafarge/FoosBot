from slacker import Slacker
import challonge

class FoosBotson:
    
    def __init__(self,
                 challonge_tournament_name,
                 api_token='xoxb-15050499792-qRGSf7w5Qv0Eitp7XMoC8w39',
                 slack_username="Foo Botson",
                 slack_icon_url='http://i.imgur.com/GlnLNWg.jpg',
                 challonge_api_key='ubxCn7J3myaGWsYLeFliIIFD53HhUJQZdgUOlEvY',
                 challonge_username='nlafarge'):

        self.slack = Slacker(api_token)
        self.slack_default_username = slack_username
        self.slack_default_icon_url = slack_icon_url
        self.nick_slack_id = 'U0EFNV9SN'

        _tournament_name = 'amadeus-%s' % challonge_tournament_name
        challonge.set_credentials(challonge_username, challonge_api_key)
        self.tournament = challonge.tournaments.show(_tournament_name)
        self.matches = challonge.matches.index(_tournament_name)
        # TODO: associate matches with winners. Right now, the

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

        self.slack.chat.post_message(channel,
                                     message,
                                     username=username,
                                     icon_url=icon,
                                     link_names=1)

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
        response = self.slack.im.open(user=user_id)
        channel_id = response.body['channel']['id']
        self.post_message_to_chat(channel_id, message, username=username, icon=icon)


if __name__ == '__main__':
    foosbot = FoosBotson('weekly_4')
    print foosbot.tournament['id']
