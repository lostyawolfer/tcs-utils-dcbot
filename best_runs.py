import discord
import config
from dataclasses import dataclass

@dataclass
class RunMember:
    member: discord.Member
    is_leader: bool = False
    is_dead: bool = False
    is_disconnected: bool = False

    @property
    def display_name(self):
        return self.member.display_name if self.member else '???'


    @property
    def emoji(self):
        emoji = []
        if self.is_leader:
            emoji.append(config.emoji['leader'])
        if self.is_dead:
            emoji.append(config.emoji['death'])
        if self.is_disconnected:
            emoji.append(config.emoji['disconnect'])
        if not emoji:
            emoji.append(config.emoji['blank'])
        return ''.join(config.emoji)




@dataclass
class RunDetails:
    run_type: str
    route: str
    death_point: tuple[str, int]
    reason: str
    participants: list[RunMember]
    is_new_best: bool = False
    is_finished: bool = False

    @property
    def max_doors(self) -> int | None:
        doors = 0
        route = self.route

        if route.startswith('b'):
            doors += 50
            route = route[1:]

        if route.startswith('h'):
            doors += 100
            route = route[1:]

        if route.startswith('r'):
            if self.route.startswith('r'):
                doors += 200
                if len(self.route.replace('-l', '')) > 1:
                    doors += 33
            else:
                doors = doors - 40 + 200 + 33
            route = route[1:]
            if self.route.startswith('h'):
                doors += 33

        if route.startswith('o'):
            if self.route.startswith('o'):
                doors += 35
            else:
                doors = doors - 10 + 35
            route = route[1:]

        if route.startswith('m'):
            if 'o' in self.route:
                doors += 50
            else:
                doors += 100

        if 'r' in self.route and '-l' in self.route:
            doors += 800

        return doors

    @property
    def progress_doors(self) -> int:
        progress = 0

        if self.death_point[0] == 'b' and not -50 <= self.death_point[1] <= 0:
            raise ValueError('how do u die in the backdoor but not in doors -50 to 0')
        if self.death_point[0] == 'h' and not 0 <= self.death_point[1] <= 100:
            raise ValueError('how do u die in the hotel but not in doors 0 to 100')
        if self.death_point[0] == 'm' and 'o' not in self.route and not 100 <= self.death_point[1] <= 200:
            raise ValueError('how do u die in the mines but not in doors 100 to 200')
        if self.death_point[0] == 'm' and 'o' in self.route and not 150 <= self.death_point[1] <= 200:
            raise ValueError('how do u die in the mines but not in doors 150 to 200 if u have outdoors')
        if self.death_point[0] == 'r' and not 0 <= self.death_point[1] <= 1000:
            raise ValueError('how do u die in the rooms but not in doors a-000 to a-1000')

        if self.death_point[0] == 'o':
            progress += self.death_point[1] / 2550 * 35
        if self.route.startswith('b'):
            progress += 50
        if 'r' in self.route and self.death_point[0] == 'h' and self.death_point[1] >= 67:
            progress = progress - 7 + 200
        elif 'r' in self.route and self.death_point[0] == 'h' and 61 <= self.death_point[1] <= 67:
            raise ValueError('how do u die in doors 61-67 if you go to the rooms')
        if self.death_point[0] == 'r' and '-l' not in self.route:
            progress += max(self.death_point[1], 200)
        elif self.death_point[0] == 'r' and '-l' in self.route:
            progress += self.death_point[1]
        if self.death_point[0] == 'h':
            progress += self.death_point[1]
        if self.death_point[0] == 'm':
            progress += self.death_point[1]
            if 'o' in self.route:
                progress -= 50

        return progress

    @property
    def progress_percent(self) -> float:
        if self.max_doors is None or self.progress_doors is None:
            return 0.0  # Handle cases where max_doors or progress_doors is None
        return min(self.progress_doors / self.max_doors * 100, 99.9)

    @property
    def message_text(self) -> str:
        route = []
        if 'b' in self.route:
            route.append('backdoor')
        if 'h' in self.route:
            route.append('hotel')
        if 'r' in self.route:
            route.append('rooms')
            if len(self.route.replace('-l', '')) > 1:
                route.append('hotel')
        if 'o' in self.route:
            route.append('outdoors')
        if 'm' in self.route:
            route.append('mines')

        current_stage = self.death_point[0]
        current_value = self.death_point[1]

        if current_stage == "r":
            current_display = f"a-{current_value:03d}"
        elif current_stage == "o":
            current_display = f"{current_value}m"
        else:
            current_display = current_value

        if current_stage == "h" and "rooms" in route:
            current_stage_index = 3 if current_value > 67 else 1
        else:
            current_stage_index = next(
                (i for i, s in enumerate(route) if s[0] == current_stage), -1
            )

        progress_lines = []
        for i, stage in enumerate(route):
            if i == current_stage_index:
                progress_lines.append(f"**{stage}** `{current_display}`")
            elif i < current_stage_index:
                progress_lines.append(f"{stage} `complete`")
            else:
                progress_lines.append(f"~~{stage}~~")

        progress = "\n".join(progress_lines)

        sorted_participants = sorted(
            self.participants,
            key=lambda p: (not p.is_leader, p.display_name.lower()),
        )

        participant_lines = []
        for i, p in enumerate(sorted_participants):
            member_mention = p.member.mention if p.member else "@???"
            participant_lines.append(
                f"{i + 1}. {p.emoji}{member_mention} `{p.display_name}`"
            )
        participants_text = (
            "\n".join(participant_lines) if participant_lines else "[no one]"
        )

        return (
            f'# {config.emoji[f'{self.run_type}']} {"*NEW BEST!*" if self.is_new_best else ""} {round(self.progress_percent, 1)}%\n'
            f"-# `{round(self.progress_doors)}/{self.max_doors}`\n"
            f"{progress}\n"
            f"\n"
            f"## PARTICIPANTS\n"
            f"{participants_text}\n"
            f"\n"
            f"run failure reason:\n"
            f"**{self.reason}**"
        )
