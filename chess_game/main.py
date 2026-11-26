"""国际象棋 —— 表现层 / 程序入口。

运行前请先安装依赖：
    pip install -r requirements.txt
然后运行：
    python main.py
"""

import os
import sys

try:
    import pygame
except ImportError:
    sys.exit("未安装 pygame，请先运行: pip install -r requirements.txt")

import logic


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
START_BG_PATH = os.path.join(ASSETS_DIR, "start_bg.png")

SQUARE = 120
BOARD_SIZE = SQUARE * 8
MARGIN = 40
WIDTH = BOARD_SIZE + MARGIN * 2
HEIGHT = BOARD_SIZE + MARGIN * 2 + 40

LIGHT = (230, 210, 135)
DARK = (100, 135, 150)
HIGHLIGHT = (246, 246, 105, 120)
LEGAL_DOT = (60, 60, 60, 110)

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]
FONT_NAMES = [
    "notosanscjk",
    "wqy-microhei",
    "wqy-zenhei",
    "microsoftyahei",
    "simhei",
    "pingfang",
    "arialunicodems",
]

PIECE_IMG = {}


def load_font(size):
    """按候选列表加载中文字体，全部失败时退回系统默认字体。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return pygame.font.Font(path, size)
    for name in FONT_NAMES:
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size)


def _placeholder_piece(code):
    """图片缺失时生成一个文字占位图，保证程序不崩溃。"""
    surf = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
    font = load_font(SQUARE // 2)
    color = (255, 255, 255) if code.startswith("w") else (0, 0, 0)
    text = font.render(code, True, color)
    surf.blit(text, text.get_rect(center=(SQUARE // 2, SQUARE // 2)))
    return surf


def load_piece_images():
    """加载 assets/images 文件夹里的棋子图。"""
    codes = ['wp', 'wr', 'wn', 'wb', 'wq', 'wk',
             'bp', 'br', 'bn', 'bb', 'bq', 'bk']
    for code in codes:
        path = os.path.join(IMAGES_DIR, f"{code}.png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            PIECE_IMG[code] = pygame.transform.smoothscale(img, (SQUARE, SQUARE))
        else:
            print(f"缺少图片，使用占位图: {path}")
            PIECE_IMG[code] = _placeholder_piece(code)


START_BG = None
START_BTN = None


def load_start_screen():
    """加载开始界面背景图。没有就用纯色兜底。"""
    global START_BG, START_BTN
    if os.path.exists(START_BG_PATH):
        img = pygame.image.load(START_BG_PATH).convert()
        START_BG = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
    else:
        print(f"缺少开始界面背景图: {START_BG_PATH}")
        START_BG = None
    bw, bh = 260, 70
    START_BTN = pygame.Rect((WIDTH - bw) // 2, HEIGHT * 2 // 3, bw, bh)


def draw_start_screen(screen, font_big):
    if START_BG is not None:
        screen.blit(START_BG, (0, 0))
    else:
        screen.fill((100, 65, 100))

    mouse = pygame.mouse.get_pos()
    color = (170, 200, 160) if START_BTN.collidepoint(mouse) else (175, 205, 225)
    pygame.draw.rect(screen, color, START_BTN, border_radius=10)
    pygame.draw.rect(screen, (225, 230, 120), START_BTN, 3, border_radius=10)

    txt = font_big.render("start", True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=START_BTN.center))


def square_to_pixel(row, col):
    return MARGIN + col * SQUARE, MARGIN + row * SQUARE


def pixel_to_square(x, y):
    col = (x - MARGIN) // SQUARE
    row = (y - MARGIN) // SQUARE
    if 0 <= row < 8 and 0 <= col < 8:
        return int(row), int(col)
    return None


def make_initial_board():
    E = logic.EMPTY
    return [
        ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
        ['bp'] * 8,
        [E] * 8,
        [E] * 8,
        [E] * 8,
        [E] * 8,
        ['wp'] * 8,
        ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr'],
    ]


def draw_board(screen, board, font_ui,
               selected, legal_targets, status_text):
    screen.fill((30, 30, 30))

    for row in range(8):
        for col in range(8):
            x, y = square_to_pixel(row, col)
            color = LIGHT if (row + col) % 2 == 0 else DARK
            pygame.draw.rect(screen, color, (x, y, SQUARE, SQUARE))

    if selected is not None:
        x, y = square_to_pixel(*selected)
        s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
        s.fill(HIGHLIGHT)
        screen.blit(s, (x, y))

    for (r, c) in legal_targets:
        x, y = square_to_pixel(r, c)
        dot = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
        pygame.draw.circle(dot, LEGAL_DOT,
                           (SQUARE // 2, SQUARE // 2), SQUARE // 6)
        screen.blit(dot, (x, y))

    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == logic.EMPTY:
                continue
            x, y = square_to_pixel(row, col)
            img = PIECE_IMG.get(piece)
            if img is not None:
                screen.blit(img, (x, y))
            else:
                t = font_ui.render(piece, True, (0, 0, 0))
                screen.blit(t, (x + 20, y + 20))

    for i in range(8):
        letter = chr(ord('a') + i)
        t = font_ui.render(letter, True, (220, 220, 220))
        screen.blit(t, (MARGIN + i * SQUARE + SQUARE // 2 - 5, MARGIN - 30))
        screen.blit(t, (MARGIN + i * SQUARE + SQUARE // 2 - 5,
                        MARGIN + BOARD_SIZE + 5))
        num = str(8 - i)
        t = font_ui.render(num, True, (220, 220, 220))
        screen.blit(t, (MARGIN - 25, MARGIN + i * SQUARE + SQUARE // 2 - 10))
        screen.blit(t, (MARGIN + BOARD_SIZE + 8,
                        MARGIN + i * SQUARE + SQUARE // 2 - 10))

    status = font_ui.render(status_text, True, (255, 255, 200))
    screen.blit(status, (MARGIN, MARGIN + BOARD_SIZE + 25))


def ask_promotion(screen, font_ui, color):
    options = ['q', 'r', 'b', 'n']
    box_w, box_h = 360, 110
    box_x = (WIDTH - box_w) // 2
    box_y = (HEIGHT - box_h) // 2
    pygame.draw.rect(screen, (50, 50, 50), (box_x, box_y, box_w, box_h))
    pygame.draw.rect(screen, (200, 200, 200), (box_x, box_y, box_w, box_h), 2)
    tip = font_ui.render("升变：按 Q/R/B/N 选择", True, (255, 255, 255))
    screen.blit(tip, (box_x + 20, box_y + 15))

    for i, p in enumerate(options):
        code = color + p
        img = PIECE_IMG.get(code)
        x = box_x + 30 + i * 80
        y = box_y + 45
        if img:
            screen.blit(pygame.transform.smoothscale(img, (50, 50)), (x, y))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                k = pygame.key.name(event.key).lower()
                if k in options:
                    return k


def select_square(board, sq, turn, moved_state, en_passant):
    """选中一格并返回该棋子所有合法落点。"""
    legal_targets = []
    for mv in logic.iter_pseudo_moves(board, turn, moved_state, en_passant):
        if mv[0] != sq:
            continue
        if logic.is_legal_move(board, mv[0], mv[1], moved_state, turn,
                               en_passant, mv[2]):
            if mv[1] not in legal_targets:
                legal_targets.append(mv[1])
    return legal_targets


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("国际象棋")

    font_big = load_font(40)
    font_ui = load_font(18)
    load_piece_images()
    load_start_screen()

    board = make_initial_board()
    moved_state = set()
    en_passant = None
    turn = logic.WHITE
    selected = None
    legal_targets = []
    status_text = "白方走棋"
    scene = "start"

    while True:
        if scene == "start":
            draw_start_screen(screen, font_big)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if (event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                        and START_BTN.collidepoint(event.pos)):
                    scene = "playing"
            continue

        draw_board(screen, board, font_ui,
                   selected, legal_targets, status_text)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                continue

            sq = pixel_to_square(*event.pos)
            if sq is None:
                continue

            if selected is None:
                piece = board[sq[0]][sq[1]]
                if piece != logic.EMPTY and piece[0] == turn:
                    selected = sq
                    legal_targets = select_square(
                        board, sq, turn, moved_state, en_passant)
                continue

            if sq == selected:
                selected = None
                legal_targets = []
                continue

            target_piece = board[sq[0]][sq[1]]
            if target_piece != logic.EMPTY and target_piece[0] == turn:
                selected = sq
                legal_targets = select_square(
                    board, sq, turn, moved_state, en_passant)
                continue

            matches = []
            for mv in logic.iter_pseudo_moves(
                    board, turn, moved_state, en_passant):
                if mv[0] != selected or mv[1] != sq:
                    continue
                if logic.is_legal_move(board, mv[0], mv[1],
                                       moved_state, turn,
                                       en_passant, mv[2]):
                    matches.append(mv)

            if not matches:
                selected = None
                legal_targets = []
                continue

            if len(matches) > 1:
                draw_board(screen, board, font_ui,
                           selected, legal_targets, status_text)
                promo = ask_promotion(screen, font_ui, turn)
                chosen = next(mv for mv in matches if mv[2] == promo)
            else:
                chosen = matches[0]

            success, new_ep = logic.make_move(
                board, chosen[0], chosen[1], moved_state,
                en_passant=en_passant, promotion=chosen[2],
                pre_validated=True,
            )
            selected = None
            legal_targets = []
            if not success:
                continue

            en_passant = new_ep
            turn = logic._enemy_of(turn)
            status = logic.game_status(board, turn, moved_state, en_passant)

            if status == 'checkmate':
                winner = "白方" if turn == logic.BLACK else "黑方"
                status_text = f"{winner}获胜！（将死）"
            elif status == 'stalemate':
                status_text = "和棋（无子可动）"
            elif status == 'check':
                status_text = f"{logic._color_name(turn)}被将军！"
            else:
                status_text = f"{logic._color_name(turn)}走棋"


if __name__ == '__main__':
    main()
