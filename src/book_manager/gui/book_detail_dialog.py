"""保存済み書籍を大きな書影とともに閲覧する。外部通信・保存は行わない。"""
import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageOps, ImageTk

from book_manager.gui.window_positioning import center_window_on_parent

logger = logging.getLogger(__name__)

LABELS = {
    'id': 'ID', 'title': '書籍名', 'author': '著者名', 'publisher': '出版社',
    'publication_format': '出版形態', 'isbn': 'ISBN', 'reference_isbn': '参照ISBN',
    'magazine_code': '雑誌コード', 'completion_month': '読了年月',
    'reading_status': '読書状態', 'is_favorite': 'お気に入り', 'rating': '評価',
    'tags': 'タグ', 'description': '内容紹介', 'notes': '備考',
    'created_at': '登録日時', 'updated_at': '更新日時',
    'cover_image_url': '書影URL', 'cover_image_path': '書影保存パス',
}


def detail_sections(book, authors=(), histories=()):
    """全書籍項目と関連情報を欠落・切り詰めなく表示用に変換する。"""
    order = ('id', 'title', 'author', 'publisher', 'publication_format', 'isbn',
             'reference_isbn', 'magazine_code', 'completion_month', 'reading_status',
             'is_favorite', 'rating', 'tags', 'description', 'notes', 'created_at',
             'updated_at', 'cover_image_url', 'cover_image_path')
    result = []
    for name in order:
        value = getattr(book, name)
        if name == 'is_favorite':
            value = 'はい' if value else 'いいえ'
        elif name == 'reading_status':
            value = {'unread': '未読', 'reading': '読書中', 'completed': '読了'}.get(value, value)
        elif name == 'tags':
            value = ' ／ '.join(value)
        elif name == 'rating' and value is not None:
            value = f'{value} / 5'
        result.append((LABELS[name], str(value) if value is not None and value != '' else '未設定'))
    result.insert(3, ('管理著者', '\n'.join(f'{a.name} [ID:{a.id}]' for a in authors) or '未設定'))
    history_text = []
    for h in histories:
        history_text.append(
            f'ID: {h.id}\n開始日: {h.started_on or "未設定"}　読了日: {h.completed_on or "未設定"}'
            f'\nメモ: {h.notes or "未設定"}\n登録日時: {h.created_at or "未設定"}'
            f'\n更新日時: {h.updated_at or "未設定"}')
    result.append(('読書履歴', '\n\n'.join(history_text) or '登録なし'))
    return result


def ordered_histories(histories):
    """読了日、未読了なら開始日・登録日時の順で読書回を並べる。"""
    return sorted(histories, key=lambda h: (
        h.completed_on or h.started_on or (h.created_at or '')[:10],
        h.created_at or '', h.id or 0))


def history_date(value):
    return value.replace('-', '/') if value else '未設定'


def load_cover(path):
    """既存の画像だけを読む。欠落・破損時も詳細本文は閲覧可能にする。"""
    if path is None:
        return None
    try:
        with Image.open(path) as source:
            if source.width * source.height > 20_000_000:
                return None
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image.thumbnail((320, 480), Image.Resampling.LANCZOS)
            return image
    except (OSError, ValueError, Image.DecompressionBombError):
        logger.warning('詳細画面の書影を読み込めませんでした。', exc_info=True)
        return None


class BookDetailDialog:
    def __init__(self, parent, *, book, authors=(), histories=(), cover_path=None):
        histories = tuple(histories)
        self.window = tk.Toplevel(parent)
        self.window.title('書籍詳細')
        self.window.transient(parent)
        # 装飾枠の余裕を確保し、画面の高さに応じてさらに縮める。
        height = min(640, max(1, parent.winfo_screenheight() - 100))
        width = min(1060, max(1, parent.winfo_screenwidth() - 80))
        self.window.geometry(f'{width}x{height}')
        self.window.resizable(True, False)
        self.window.maxsize(parent.winfo_screenwidth(), height)
        outer = ttk.Frame(self.window, padding=10)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='保存済みの書籍情報（閲覧専用）／入力中の未保存の変更は含みません。').pack(anchor='w')
        body = ttk.Frame(outer)
        body.pack(fill='both', expand=True, pady=8)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        cover = ttk.Frame(body, width=330)
        cover.grid(row=0, column=0, sticky='ns', padx=(0, 12))
        self._photo = None
        image = load_cover(cover_path)
        if image is not None:
            # 小さい画面でも閉じる操作・本文を押し出さない。
            image.thumbnail((320, max(1, height - 125)), Image.Resampling.LANCZOS)
            self._photo = ImageTk.PhotoImage(image, master=self.window)
        ttk.Label(cover, image=self._photo or '',
                  text='' if self._photo else '書影なし／画像を読み込めません').pack(expand=True)
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky='nsew')
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        canvas = tk.Canvas(right, highlightthickness=0, width=640)
        canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(right, command=canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scroll.set)
        form = ttk.Frame(canvas, padding=(0, 0, 8, 0))
        item = canvas.create_window((0, 0), window=form, anchor='nw')
        form.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
        form.columnconfigure(1, weight=1, uniform='value')
        form.columnconfigure(3, weight=1, uniform='value')
        values = dict(detail_sections(book, authors, histories))
        self._fields = {}

        def wheel(event):
            canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
            return 'break'

        canvas.bind('<MouseWheel>', wheel)
        form.bind('<MouseWheel>', wheel)

        def field(label, row, column=0, *, wide=False, lines=1):
            caption = ttk.Label(form, text=label)
            caption.grid(row=row, column=column, sticky='nw', padx=(0, 8), pady=4)
            caption.bind('<MouseWheel>', wheel)
            if lines == 1:
                widget = ttk.Entry(form, width=18)
                widget.insert(0, values[label])
                widget.configure(state='readonly')
                widget.bind('<MouseWheel>', wheel)
            else:
                box = ttk.Frame(form)
                box.grid(row=row, column=column + 1, columnspan=3 if wide else 1,
                         sticky='nsew', pady=4, padx=(0, 10))
                box.columnconfigure(0, weight=1)
                widget = tk.Text(box, height=lines, width=25, wrap='word', padx=6, pady=4)
                widget.grid(row=0, column=0, sticky='nsew')
                bar = ttk.Scrollbar(box, command=widget.yview)
                bar.grid(row=0, column=1, sticky='ns')
                widget.configure(yscrollcommand=bar.set)
                widget.insert('1.0', values[label])
                widget.configure(state='disabled')
            if lines == 1:
                widget.grid(row=row, column=column + 1, columnspan=3 if wide else 1,
                            sticky='ew', pady=4, padx=(0, 10))
            self._fields[label] = widget

        field('書籍名', 0, wide=True)
        field('著者名', 1, wide=True)
        field('出版社', 2)
        field('出版形態', 2, 2)
        field('ISBN', 3)
        field('参照ISBN', 3, 2)
        field('雑誌コード', 4)
        field('読了年月', 4, 2)
        field('読書状態', 5)
        field('評価', 5, 2)
        field('お気に入り', 6)
        field('ID', 6, 2)
        field('タグ', 7, wide=True)
        field('管理著者', 8, wide=True, lines=2)
        field('内容紹介', 9, wide=True, lines=6)
        field('備考', 10, wide=True, lines=4)
        self._create_history_panel(form, histories, row=11)
        field('登録日時', 12)
        field('更新日時', 12, 2)
        field('書影URL', 13, wide=True)
        field('書影保存パス', 14, wide=True)
        self._canvas = canvas
        ttk.Button(outer, text='閉じる', command=self.window.destroy).pack(anchor='e')
        self.window.bind('<Escape>', lambda event: self.window.destroy())
        self.window.update_idletasks()
        # 高DPIのタイトルバー・枠も考慮して700pxから差し引く。
        border_allowance = max(60, 2 * max(0, self.window.winfo_rooty() - self.window.winfo_y()))
        height = min(height, max(1, 700 - border_allowance))
        self.window.maxsize(parent.winfo_screenwidth(), height)
        self.window.geometry(f'{width}x{height}')
        center_window_on_parent(self.window, parent)

    def _create_history_panel(self, parent, histories, *, row):
        panel = ttk.LabelFrame(parent, text='読書履歴', padding=8)
        panel.grid(row=row, column=0, columnspan=4, sticky='ew', pady=8, padx=(0, 10))
        panel.columnconfigure(0, weight=1)
        items = ordered_histories(histories)
        self._history_items = {str(index): h for index, h in enumerate(items, 1)}
        ttk.Label(panel, text=f'全{len(items)}回 ／ 行を選択するとメモを表示します。'
                  if items else '読書履歴は登録されていません。').grid(
                      row=0, column=0, columnspan=2, sticky='w', pady=(0, 5))
        tree = ttk.Treeview(panel, columns=('round', 'started', 'completed'),
                            show='headings', height=4, selectmode='browse')
        for name, title, width in (('round', '回', 50), ('started', '読書開始日', 140),
                                   ('completed', '読了日', 140)):
            tree.heading(name, text=title)
            tree.column(name, width=width, minwidth=40, anchor='center', stretch=name != 'round')
        tree.grid(row=1, column=0, sticky='ew')
        bar = ttk.Scrollbar(panel, command=tree.yview)
        bar.grid(row=1, column=1, sticky='ns')
        tree.configure(yscrollcommand=bar.set)
        for key, history in self._history_items.items():
            tree.insert('', 'end', iid=key, values=(key, history_date(history.started_on),
                                                    history_date(history.completed_on)))
        self._history_tree = tree
        self._history_caption = tk.StringVar(master=self.window, value='メモ')
        ttk.Label(panel, textvariable=self._history_caption).grid(row=2, column=0, sticky='w', pady=(7, 3))
        note = tk.Text(panel, height=4, width=30, wrap='word', padx=6, pady=4)
        note.grid(row=3, column=0, sticky='ew')
        note_bar = ttk.Scrollbar(panel, command=note.yview)
        note_bar.grid(row=3, column=1, sticky='ns')
        note.configure(yscrollcommand=note_bar.set, state='disabled')
        self._history_note = note
        self._history_metadata = tk.StringVar(master=self.window)
        ttk.Label(panel, textvariable=self._history_metadata, wraplength=500).grid(
            row=4, column=0, columnspan=2, sticky='w', pady=(4, 0))
        tree.bind('<<TreeviewSelect>>', self._on_history_selected)
        if items:
            latest = str(len(items))
            tree.selection_set(latest)
            tree.focus(latest)
            tree.see(latest)
        self._on_history_selected()

    def _on_history_selected(self, event=None):
        selected = self._history_tree.selection()
        key = selected[0] if selected else None
        history = self._history_items.get(key)
        self._history_caption.set(f'第{key}回のメモ' if history else 'メモ')
        text = (history.notes or 'メモは登録されていません。') if history else '読書履歴は登録されていません。'
        self._history_note.configure(state='normal')
        self._history_note.delete('1.0', 'end')
        self._history_note.insert('1.0', text)
        self._history_note.configure(state='disabled')
        self._history_note.yview_moveto(0)
        self._history_metadata.set(
            f'履歴ID: {history.id}　登録日時: {history.created_at or "未設定"}　'
            f'更新日時: {history.updated_at or "未設定"}' if history else '')

    def show(self):
        self.window.grab_set()
        self._fields['書籍名'].focus_set()
        self.window.wait_window()
