import discord
from discord.ext import commands
from collections import OrderedDict
import asyncio
import inspect

class PaginatorSession:
    '''
    Class that interactively paginates a set of embeds

    - Made by verixx

    Parameters
    ------------
    ctx: Context
        The context of the command.
    timeout:
        How long to wait for before the session closes
    pages: List[discord.Embed]
        A list of entries to paginate.

    Methods
    -------
    add_page:
        Add an embed to paginate
    run:
        Run the interactive session
    close:
        Forcefully destroy a session
    '''
    def __init__(self, ctx, timeout=60, *, pages=[], page_nums=True, help_color=0x00FFFF):
        self.ctx = ctx
        self.timeout = timeout
        self.pages = pages
        self.running = False
        self.base = None
        self.current = 0
        self.reaction_map = OrderedDict({
            '⏮': self.first_page,
            '◀': self.previous_page,
            '⏹': self.close,
            '▶': self.next_page,
            '⏭': self.last_page,
            '🔢': self.ask_for_page,
            '🤔': self.show_help_page,
            })
        self.help_color = help_color
        self.page_num_enabled = page_nums

    def add_page(self, embed):
        if isinstance(embed, discord.Embed):
            self.pages.append(embed)
        else:
            raise TypeError('Page must be an Embed object.')

    def valid_page(self, index):
        if index < 0 or index+1 > len(self.pages):
            return False
        else:
            return True

    async def show_page(self, index: int):
        if not self.valid_page(index):
            return

        self.current = index
        page = self.pages[index]

        if self.page_num_enabled:
            fmt = f'Page {index+1}/{len(self.pages)}'
            page.set_footer(text=fmt)

        if self.running:
            await self.base.edit(embed=page)
        else:
            self.running = True
            self.base = await self.ctx.send(embed=page)
            for reaction in self.reaction_map.keys():
                if len(self.pages) == 2 and reaction in '⏮⏭':
                    continue
                await self.base.add_reaction(reaction)

    def react_check(self, reaction, user):
        if user.id != self.ctx.author.id:
            return False
        if reaction.message.id != self.base.id:
            return False
        if reaction.emoji in self.reaction_map.keys():
            return True

    async def run(self):
        if not self.running:
            await self.show_page(0)
        while self.running:
            try:
                reaction, user = await self.ctx.bot.wait_for('reaction_add', check=self.react_check, timeout=self.timeout)
            except asyncio.TimeoutError:
                self.paginating = False
                try:
                    await self.base.clear_reactions()
                except:
                    pass
                finally:
                    break
            try:
                await self.base.remove_reaction(reaction, user)
            except:
                pass

            show_page = self.reaction_map.get(reaction.emoji)

            await show_page()

    def previous_page(self):
        '''Go to the previous page.'''
        return self.show_page(self.current-1)

    def next_page(self):
        '''Go to the next page'''
        return self.show_page(self.current+1)

    def first_page(self):
        '''Go to immediately to the first page'''
        return self.show_page(0)

    def last_page(self):
        '''Go to immediately to the last page'''
        return self.show_page(len(self.pages)-1)

    async def show_help_page(self):
        '''Shows this page.'''
        em = discord.Embed(color=self.help_color)
        em.title = 'Pagination Session - Help'

        em.description = 'React with each of the following ' \
                         'reactions to navigate.'
        help = ''

        for reaction, callback in self.reaction_map.items():
            doc = inspect.getdoc(callback)
            help += f'{reaction} - {doc}\n'
            
        em.add_field(name='Reactions?', value=help)
        
        if self.page_num_enabled:
            fmt = f'Page {self.current+1}/{len(self.pages)}'
            em.set_footer(text=fmt)

        await self.base.edit(embed=em)

    def close(self, delete=True):
        '''Delete this embed.'''
        self.running = False
        if delete:
            return self.base.delete()

    def message_check(self, m):
        return m.author == self.ctx.author and \
            self.ctx.channel == m.channel and \
            m.content.isdigit()

    async def ask_for_page(self):
        '''Type in the page number.'''
        to_delete = []
        
        x = await self.ctx.send('What page do you want to go to?')
        to_delete.append(x)

        try:
            msg = await self.ctx.bot.wait_for('message', check=self.message_check, timeout=30.0)
        except asyncio.TimeoutError:
            x = await self.ctx.send('Took too long.')
            to_delete.append(x)
        else:
            page = int(msg.content)
            to_delete.append(msg)
            if page != 0 and page <= len(self.pages):
                await self.show_page(page-1)
            else:
                x = await self.ctx.send(f'Invalid page given. ({page}/{len(self.pages)})')
                to_delete.append(x)
        try:
            await asyncio.sleep(5)
            await self.ctx.channel.delete_messages(to_delete)
        except Exception:
            pass
