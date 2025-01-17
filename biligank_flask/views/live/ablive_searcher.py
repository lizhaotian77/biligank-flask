from collections import defaultdict
from typing import Any, Optional

from biligank_flask.sqldb import db
from biligank_flask.utils import get_date

__all__ = 'AbliveSearcher',


DailyAbliveData = tuple[list[dict[str, Any]], set[Any]]


class AbliveSearcher:
    def __init__(self, road: str, limits: int) -> None:
        self.road = road
        self.limits = limits
        self.tables: list = []
        self.last_table = ''

    def update_tables(self) -> None:
        # error: get_bind() got an unexpected keyword argument 'bind'
        # https://github.com/pallets-eco/flask-sqlalchemy/issues/953
        # resolved in flask-sqlalchemy 3.0.0 released on 2022.10.04
        rs_tup = db.session.execute(
            'show tables;',
            bind=db.get_engine(bind_key=f'{self.road}')
        ).all()
        tables = [rs[0] for rs in rs_tup]
        tables.sort(reverse=False)
        if self.road in ('tp', 'ablive_sc'):
            self.tables = tables
        else:
            self.tables = tables[-15:]
        self.last_table = tables[-1]

    def more(self, uid: int, offset: str) -> tuple[list[Optional[Any]], str, bool, set[Optional[int]]]:  # noqa
        road = self.road

        if get_date() != self.last_table or not self.tables:
            self.update_tables()

        try:
            if offset == '0':
                offset = self.last_table
                table_idx = self.tables.index(offset) + 1
            else:
                table_idx = self.tables.index(offset)
        except Exception as e:
            raise e

        data = []
        liverids = set()
        while table_idx > 0:
            table_idx -= 1
            table = self.tables[table_idx]

            f = getattr(self, f'daily_{road}')
            _data, _liverids = f(table, uid)
            data.extend(_data)
            liverids |= _liverids

            if len(data) >= self.limits:
                break

        db.session.commit()

        next_offset = table
        has_more = False if table_idx == 0 else True

        return data, next_offset, has_more, liverids

    def daily_tp(self, table: str, uid: int) -> DailyAbliveData:
        date_tp_list = []

        rs_tup = db.session.execute(
            f'select title, c_ts, last_update, watched_num, area_name, cover from `{table}` where uid = :uid ORDER BY _id DESC',  # noqa
            {'uid': uid},
            bind=db.get_engine(bind_key='tp')
        ).all()
        print(rs_tup)
        for tp in rs_tup:
            date_tp_list.append(tp)

        return date_tp_list, set()

    def daily_ablive_dm(self, table: str, uid: int) -> DailyAbliveData:
        date_danmaku_cards = []
        _livers = set()

        rs_tup = db.session.execute(
            f'select ts, liverid, text from `{table}` where uid = :uid ORDER BY _id DESC',  # noqa
            {'uid': uid},
            bind=db.get_engine(bind_key='ablive_dm')
        ).all()
        _tmp = defaultdict(list)
        for ts, liverid, text in rs_tup:
            _tmp[liverid].append((ts, text))
            _livers.add(liverid)

        for liverid, danmakus in _tmp.items():
            card = {
                'date': table,
                'liverid': liverid,
                'danmakus': danmakus,
            }
            date_danmaku_cards.append(card)

        return date_danmaku_cards, _livers

    def daily_ablive_en(self, table: str, uid: int) -> DailyAbliveData:
        date_entry_list = []
        _livers = set()

        rs_tup = db.session.execute(
            f'select ts, liverid from `{table}` where uid = :uid ORDER BY _id DESC',  # noqa
            {'uid': uid},
            bind=db.get_engine(bind_key='ablive_en')
        ).all()
        for entry in rs_tup:
            date_entry_list.append(dict(entry))
            _livers.add(entry['liverid'])

        return date_entry_list, _livers

    def daily_ablive_gf(self, table: str, uid: int) -> DailyAbliveData:
        date_gift_list = []
        _livers = set()

        rs_tup = db.session.execute(
            f'select ts, liverid, gift_info, gift_cost from `{table}` where uid = :uid ORDER BY _id DESC',  # noqa
            {'uid': uid},
            bind=db.get_engine(bind_key='ablive_gf')
        ).all()
        for gift in rs_tup:
            date_gift_list.append(dict(gift))
            _livers.add(gift['liverid'])

        return date_gift_list, _livers

    def daily_ablive_sc(self, table: str, uid: int) -> DailyAbliveData:
        date_sc_list = []
        liverid = uid

        rs_tup = db.session.execute(
            f'select ts, uid, uname, text, sc_price from `{table}` where liverid = :liverid ORDER BY _id DESC',  # noqa
            {'liverid': liverid},
            bind=db.get_engine(bind_key='ablive_sc')
        ).all()
        for superchat in rs_tup:
            # superchat['sc_price'] = int(superchat['sc_price'])
            date_sc_list.append(dict(superchat))

        return date_sc_list, set()
