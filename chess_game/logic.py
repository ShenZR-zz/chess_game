# ===== 常量 =====
EMPTY = '--'
WHITE, BLACK = 'w', 'b'
PROMOTION_CHOICES = ('q', 'r', 'b', 'n')


# ===== 坐标转换 =====
def pos_to_index(pos):
    """'e2' -> (6, 4)。非法输入抛 ValueError。"""
    if not isinstance(pos, str) or len(pos) != 2:
        raise ValueError(f"坐标格式错误: {pos!r}")
    col_letter, row_number = pos[0], pos[1]
    if not ('a' <= col_letter <= 'h') or not ('1' <= row_number <= '8'):
        raise ValueError(f"坐标越界: {pos!r}")
    return (8 - int(row_number), ord(col_letter) - ord('a'))


def index_to_pos(pos):
    """(6, 4) -> 'e2'"""
    row, col = pos
    return chr(ord('a') + col) + str(8 - row)


def _in_board(row, col):
    return 0 <= row < 8 and 0 <= col < 8


def _enemy_of(color):
    return BLACK if color == WHITE else WHITE


def _color_name(color):
    return '白方' if color == WHITE else '黑方'


# ===== 打印棋盘 =====
def print_board(board):
    print('   a b c d e f g h')
    for row in range(8):
        line = f'{8 - row}  '
        for col in range(8):
            line += board[row][col] + ' '
        print(line)
    print('   a b c d e f g h')
    print('----------------')


def find_king(board, color):
    target = color + 'k'
    for row in range(8):
        for col in range(8):
            if board[row][col] == target:
                return (row, col)
    return None


# ============================================================
# 各棋子走法（只查规则，不含送王检查、不吃己方子由上层处理）
# ============================================================

def is_valid_pawn(piece, from_pos, to_pos, board):
    fr, fc = from_pos
    tr, tc = to_pos
    color = piece[0]

    if color == WHITE:
        direction = -1
        start_row = 6
    else:
        direction = 1
        start_row = 1

    # 直走一格
    if fc == tc and tr == fr + direction:
        return board[tr][tc] == EMPTY

    # 直走两格
    if fc == tc and fr == start_row and tr == fr + 2 * direction:
        return (board[fr + direction][fc] == EMPTY and
                board[tr][tc] == EMPTY)

    # 斜吃（普通吃子；吃过路兵由上层单独处理）
    if abs(tc - fc) == 1 and tr == fr + direction:
        target = board[tr][tc]
        return target != EMPTY and target[0] != color

    return False


def is_valid_rook(piece, from_pos, to_pos, board):
    fr, fc = from_pos
    tr, tc = to_pos

    if fc == tc:
        step = 1 if tr > fr else -1
        for r in range(fr + step, tr, step):
            if board[r][tc] != EMPTY:
                return False
        return True

    if fr == tr:
        step = 1 if tc > fc else -1
        for c in range(fc + step, tc, step):
            if board[fr][c] != EMPTY:
                return False
        return True

    return False


def is_valid_knight(piece, from_pos, to_pos, board):
    fr, fc = from_pos
    tr, tc = to_pos
    return ((abs(tc - fc) == 1 and abs(tr - fr) == 2) or
            (abs(tc - fc) == 2 and abs(tr - fr) == 1))


def is_valid_bishop(piece, from_pos, to_pos, board):
    fr, fc = from_pos
    tr, tc = to_pos

    if abs(tc - fc) != abs(tr - fr):
        return False

    ud = 1 if tr > fr else -1
    lr = 1 if tc > fc else -1

    for r, c in zip(range(fr + ud, tr, ud),
                    range(fc + lr, tc, lr)):
        if board[r][c] != EMPTY:
            return False
    return True


def is_valid_queen(piece, from_pos, to_pos, board):
    return (is_valid_rook(piece, from_pos, to_pos, board) or
            is_valid_bishop(piece, from_pos, to_pos, board))


# ============================================================
# 攻击判定
# ============================================================

def is_attacked(board, pos, enemy_color, moved_state=None):
    """判断 pos 格是否被 enemy_color 攻击（不考虑 pos 上放的是什么）。

    对兵和王单独处理，避免复用 is_valid_move 造成递归/性能问题。
    """
    tr, tc = pos

    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece == EMPTY or piece[0] != enemy_color:
                continue

            kind = piece[1]

            # 兵：单独判断
            if kind == 'p':
                direction = -1 if enemy_color == WHITE else 1
                if tr == row + direction and abs(tc - col) == 1:
                    return True
                continue

            # 王：单独判断
            if kind == 'k':
                if abs(tr - row) <= 1 and abs(tc - col) <= 1:
                    return True
                continue

            if is_valid_move(piece, (row, col), pos, board,
                             moved_state=moved_state,
                             check_castling=False):
                return True

    return False


# ============================================================
# 易位
# ============================================================

def is_valid_castle(board, from_pos, rook_pos, moved_state):
    """
    判断王从 from_pos 易位到车 rook_pos 一侧是否合法。
    moved_state: set of (row, col)，记录了"曾经位于该格或被该格上的子动过"的格子。
    """
    fr, fc = from_pos
    color = board[fr][fc][0]

    # 王和车都必须从未动过
    if from_pos in moved_state or rook_pos in moved_state:
        return False

    # 车必须在初始位置且是己方车
    if board[rook_pos[0]][rook_pos[1]] != color + 'r':
        return False

    # 王与车之间必须全空
    min_col = min(fc, rook_pos[1]) + 1
    max_col = max(fc, rook_pos[1])
    for c in range(min_col, max_col):
        if board[fr][c] != EMPTY:
            return False

    # 起点、经过格、终点都不能被攻击
    enemy_color = _enemy_of(color)
    step = 1 if rook_pos[1] > fc else -1
    for c in (fc, fc + step, fc + 2 * step):
        if is_attacked(board, (fr, c), enemy_color, moved_state):
            return False

    return True


def is_valid_king(piece, from_pos, to_pos, board,
                  moved_state=None, check_castling=True):
    fr, fc = from_pos
    tr, tc = to_pos

    if fr == tr and fc == tc:
        return False

    if abs(tr - fr) <= 1 and abs(tc - fc) <= 1:
        return True

    if check_castling and abs(tc - fc) == 2 and tr == fr:
        rook_pos = (fr, 7) if tc > fc else (fr, 0)
        if board[rook_pos[0]][rook_pos[1]] != piece[0] + 'r':
            return False
        return is_valid_castle(board, from_pos, rook_pos,
                               moved_state or set())

    return False


# ============================================================
# 走法汇总（只查规则）
# ============================================================

def is_valid_move(piece, from_pos, to_pos, board,
                  moved_state=None, check_castling=True):
    if piece == EMPTY:
        return False
    kind = piece[1]

    if kind == 'p':
        return is_valid_pawn(piece, from_pos, to_pos, board)
    elif kind == 'r':
        return is_valid_rook(piece, from_pos, to_pos, board)
    elif kind == 'n':
        return is_valid_knight(piece, from_pos, to_pos, board)
    elif kind == 'b':
        return is_valid_bishop(piece, from_pos, to_pos, board)
    elif kind == 'q':
        return is_valid_queen(piece, from_pos, to_pos, board)
    elif kind == 'k':
        return is_valid_king(piece, from_pos, to_pos, board,
                             moved_state, check_castling)
    return False


# ============================================================
# 吃过路兵
# ============================================================

def _is_en_passant_capture(board, from_pos, to_pos, color, en_passant):
    """
    判断是否构成吃过路兵。

    en_passant: (row, col) 或 None。
        表示"上一手敌方兵走两格后的中间格"，也就是本次吃过路兵时
        己方兵要落到的目标格。
    """
    if en_passant is None:
        return False

    fr, fc = from_pos
    tr, tc = to_pos
    piece = board[fr][fc]
    if piece[1] != 'p':
        return False

    direction = -1 if color == WHITE else 1
    if (tr, tc) != en_passant:
        return False
    if abs(tc - fc) != 1 or tr != fr + direction:
        return False

    # 被吃的兵在 to_pos 的"后方"（同列、原来所在行）
    captured_pos = (fr, tc)
    captured = board[captured_pos[0]][captured_pos[1]]
    if captured == EMPTY or captured[1] != 'p' or captured[0] == color:
        return False

    return True


# ============================================================
# 合法性判定（规则 + 送王检查，内部模拟后撤销）
# ============================================================

def _simulate_and_check(board, from_pos, to_pos, color,
                        moved_state, is_castle, is_en_passant,
                        promotion=None):
    """
    模拟走子（含升变），检查己方王是否被攻击。
    用 try/finally 保证撤销。
    """
    fr, fc = from_pos
    tr, tc = to_pos
    piece = board[fr][fc]

    eaten = board[tr][tc]
    eaten_en_passant_pos = None

    # 放置走子后的子（含升变）
    if piece[1] == 'p' and (tr == 0 or tr == 7) and promotion in PROMOTION_CHOICES:
        board[tr][tc] = color + promotion
    else:
        board[tr][tc] = piece
    board[fr][fc] = EMPTY

    try:
        if is_en_passant:
            cap_pos = (fr, tc)
            eaten_en_passant_pos = cap_pos
            board[cap_pos[0]][cap_pos[1]] = EMPTY

        if is_castle:
            if tc > fc:
                board[fr][5] = board[fr][7]
                board[fr][7] = EMPTY
            else:
                board[fr][3] = board[fr][0]
                board[fr][0] = EMPTY

        king_pos = find_king(board, color)
        if king_pos is None:
            return True  # 理论上不会发生；宽松处理
        return not is_attacked(board, king_pos, _enemy_of(color), moved_state)
    finally:
        # 撤销（无论是否异常）
        if is_castle:
            if tc > fc:
                board[fr][7] = board[fr][5]
                board[fr][5] = EMPTY
            else:
                board[fr][0] = board[fr][3]
                board[fr][3] = EMPTY

        if is_en_passant and eaten_en_passant_pos is not None:
            board[eaten_en_passant_pos[0]][eaten_en_passant_pos[1]] = (
                _enemy_of(color) + 'p')

        board[fr][fc] = piece
        board[tr][tc] = eaten


def is_legal_move(board, from_pos, to_pos, moved_state, color,
                  en_passant=None, promotion=None):
    """
    color 方从 from_pos 到 to_pos 是否合法（规则 + 不送王）。不修改棋盘。

    promotion: 仅当兵走到最后一排时使用；None 表示默认后。
    """
    fr, fc = from_pos
    tr, tc = to_pos

    if not (_in_board(fr, fc) and _in_board(tr, tc)):
        return False

    piece = board[fr][fc]
    if piece == EMPTY or piece[0] != color:
        return False

    target = board[tr][tc]
    if target != EMPTY and target[0] == color:
        return False

    if moved_state is None:
        moved_state = set()

    # 升变参数校验
    is_promotion = (piece[1] == 'p' and (tr == 0 or tr == 7))
    if is_promotion:
        if promotion is None:
            promotion = 'q'
        if promotion not in PROMOTION_CHOICES:
            return False
    else:
        promotion = None

    is_en_passant = _is_en_passant_capture(board, from_pos, to_pos,
                                           color, en_passant)
    is_castle = (piece[1] == 'k' and abs(tc - fc) == 2 and fr == tr)

    if not is_en_passant:
        if not is_valid_move(piece, from_pos, to_pos, board, moved_state):
            return False

    return _simulate_and_check(board, from_pos, to_pos, color,
                               moved_state, is_castle, is_en_passant,
                               promotion)


# ============================================================
# 将军判定
# ============================================================

def is_in_check(board, color, moved_state):
    king_pos = find_king(board, color)
    if king_pos is None:
        return False
    return is_attacked(board, king_pos, _enemy_of(color), moved_state)


# ============================================================
# 候选走法生成（生成器版，走法为三元组）
# ============================================================

_KNIGHT_DELTAS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                  (1, -2), (1, 2), (2, -1), (2, 1)]
_KING_DELTAS = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]
_ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def iter_pseudo_moves(board, color, moved_state, en_passant=None):
    """生成 color 方所有伪合法走法（只查规则，不查送王）。

    每条走法为 (from_pos, to_pos, promotion)。
    兵走到最后一排时生成 4 条（q/r/b/n）。
    """
    for fr in range(8):
        for fc in range(8):
            piece = board[fr][fc]
            if piece == EMPTY or piece[0] != color:
                continue
            kind = piece[1]

            if kind == 'p':
                direction = -1 if color == WHITE else 1
                start_row = 6 if color == WHITE else 1
                promotion_row = 0 if color == WHITE else 7

                tr = fr + direction
                if _in_board(tr, fc):
                    # 直走一格
                    if board[tr][fc] == EMPTY:
                        if tr == promotion_row:
                            for promo in PROMOTION_CHOICES:
                                yield (fr, fc), (tr, fc), promo
                        else:
                            yield (fr, fc), (tr, fc), None
                            # 直走两格
                            tr2 = fr + 2 * direction
                            if (fr == start_row and _in_board(tr2, fc)
                                    and board[tr2][fc] == EMPTY):
                                yield (fr, fc), (tr2, fc), None

                    # 斜吃
                    for dc in (-1, 1):
                        tc = fc + dc
                        if _in_board(tr, tc):
                            target = board[tr][tc]
                            if target != EMPTY and target[0] != color:
                                if tr == promotion_row:
                                    for promo in PROMOTION_CHOICES:
                                        yield (fr, fc), (tr, tc), promo
                                else:
                                    yield (fr, fc), (tr, tc), None
                            elif _is_en_passant_capture(board, (fr, fc), (tr, tc),
                                                        color, en_passant):
                                yield (fr, fc), (tr, tc), None

            elif kind == 'n':
                for dr, dc in _KNIGHT_DELTAS:
                    tr, tc = fr + dr, fc + dc
                    if _in_board(tr, tc):
                        target = board[tr][tc]
                        if target == EMPTY or target[0] != color:
                            yield (fr, fc), (tr, tc), None

            elif kind == 'k':
                for dr, dc in _KING_DELTAS:
                    tr, tc = fr + dr, fc + dc
                    if _in_board(tr, tc):
                        target = board[tr][tc]
                        if target == EMPTY or target[0] != color:
                            yield (fr, fc), (tr, tc), None
                # 易位
                for tc in (fc - 2, fc + 2):
                    if _in_board(fr, tc):
                        rook_pos = (fr, 7) if tc > fc else (fr, 0)
                        if board[rook_pos[0]][rook_pos[1]] == color + 'r':
                            if is_valid_castle(board, (fr, fc), rook_pos, moved_state):
                                yield (fr, fc), (fr, tc), None

            elif kind in ('r', 'b', 'q'):
                dirs = []
                if kind in ('r', 'q'):
                    dirs += _ROOK_DIRS
                if kind in ('b', 'q'):
                    dirs += _BISHOP_DIRS
                for dr, dc in dirs:
                    tr, tc = fr + dr, fc + dc
                    while _in_board(tr, tc):
                        target = board[tr][tc]
                        if target == EMPTY:
                            yield (fr, fc), (tr, tc), None
                        else:
                            if target[0] != color:
                                yield (fr, fc), (tr, tc), None
                            break
                        tr += dr
                        tc += dc


def generate_pseudo_moves(board, color, moved_state, en_passant=None):
    """列表版（保留，兼容旧调用）。"""
    return list(iter_pseudo_moves(board, color, moved_state, en_passant))


def has_any_legal_move(board, color, moved_state, en_passant=None):
    """判断 color 方是否至少有一个合法走法（边生成边验证，提前退出）。"""
    for from_pos, to_pos, promo in iter_pseudo_moves(
            board, color, moved_state, en_passant):
        if is_legal_move(board, from_pos, to_pos, moved_state,
                         color, en_passant, promo):
            return True
    return False


def generate_legal_moves(board, color, moved_state, en_passant=None):
    """生成 color 方所有合法走法。"""
    result = []
    for mv in iter_pseudo_moves(board, color, moved_state, en_passant):
        if is_legal_move(board, mv[0], mv[1], moved_state, color, en_passant, mv[2]):
            result.append(mv)
    return result


# ============================================================
# 局面状态（合并检查，避免重复生成走法）
# ============================================================

def game_status(board, color, moved_state, en_passant=None):
    """
    返回 'checkmate' / 'stalemate' / 'check' / 'ok'。
    只生成一次走法列表，比分别调用 is_checkmate / is_stalemate 高效。
    """
    in_check = is_in_check(board, color, moved_state)
    has_move = has_any_legal_move(board, color, moved_state, en_passant)
    if in_check and not has_move:
        return 'checkmate'
    if not in_check and not has_move:
        return 'stalemate'
    if in_check:
        return 'check'
    return 'ok'


def is_checkmate(board, color, moved_state, en_passant=None):
    return game_status(board, color, moved_state, en_passant) == 'checkmate'


def is_stalemate(board, color, moved_state, en_passant=None):
    return game_status(board, color, moved_state, en_passant) == 'stalemate'


# ============================================================
# 执行走子
# ============================================================

def make_move(board, from_pos, to_pos, moved_state,
              en_passant=None, promotion=None,
              pre_validated=False):
    """
    执行走子。返回 (success, new_en_passant)。

    promotion: 'q'/'r'/'b'/'n'，仅当兵走到最后一排时使用；
               若为 None，默认升变为后。
    pre_validated: 若为 True，跳过内部 is_legal_move 检查（调用者已确认合法）。
    """
    fr, fc = from_pos
    tr, tc = to_pos
    piece = board[fr][fc]

    if piece == EMPTY:
        return False, en_passant

    color = piece[0]

    # 升变参数规整
    if piece[1] == 'p' and (tr == 0 or tr == 7):
        if promotion not in PROMOTION_CHOICES:
            promotion = 'q'
    else:
        promotion = None

    if not pre_validated:
        if not is_legal_move(board, from_pos, to_pos, moved_state, color,
                             en_passant, promotion):
            return False, en_passant

    is_en_passant = _is_en_passant_capture(board, from_pos, to_pos, color, en_passant)
    is_castle = (piece[1] == 'k' and abs(tc - fc) == 2 and fr == tr)

    # 执行
    board[tr][tc] = piece
    board[fr][fc] = EMPTY

    if is_en_passant:
        board[fr][tc] = EMPTY

    if is_castle:
        if tc > fc:
            board[fr][5] = board[fr][7]
            board[fr][7] = EMPTY
            moved_state.add((fr, 7))
            moved_state.add((fr, 5))
        else:
            board[fr][3] = board[fr][0]
            board[fr][0] = EMPTY
            moved_state.add((fr, 0))
            moved_state.add((fr, 3))

    # 记录移动：原格和新格都标记
    moved_state.add((fr, fc))
    moved_state.add((tr, tc))

    # 更新 en_passant：仅当兵走两格时设置中间格
    new_en_passant = None
    if piece[1] == 'p' and abs(tr - fr) == 2:
        new_en_passant = ((fr + tr) // 2, fc)

    # 升变
    if promotion is not None:
        board[tr][tc] = color + promotion

    return True, new_en_passant


# ============================================================
# 主循环
# ============================================================

def _prompt_promotion():
    while True:
        choice = input("请选择升变棋子 (q=后, r=车, b=象, n=马): ").strip().lower()
        if choice in PROMOTION_CHOICES:
            return choice
        print("输入无效，请输入 q, r, b, 或 n。")


def main():
    board = [
        ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
        ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],
        [EMPTY] * 8,
        [EMPTY] * 8,
        [EMPTY] * 8,
        [EMPTY] * 8,
        ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],
        ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr'],
    ]

    moved_state = set()
    en_passant = None
    turn = WHITE

    while True:
        print_board(board)
        print(f'{_color_name(turn)}走棋')

        try:
            user_input = input('请输入起点和终点（例如 e2 e4): ')
        except (EOFError, KeyboardInterrupt):
            print('\n游戏结束。')
            break

        parts = user_input.split()
        if len(parts) != 2:
            print('输入格式不对，请重新输入')
            continue

        try:
            from_pos = pos_to_index(parts[0])
            to_pos = pos_to_index(parts[1])
        except ValueError as e:
            print(f'坐标错误：{e}')
            continue

        if from_pos == to_pos:
            print('起点和终点不能相同，请重新输入')
            continue

        piece = board[from_pos[0]][from_pos[1]]
        if piece == EMPTY or piece[0] != turn:
            print('这不是你的棋子')
            continue

        # 枚举所有合法走法，匹配用户起终点
        matches = []
        for mv in iter_pseudo_moves(board, turn, moved_state, en_passant):
            if mv[0] != from_pos or mv[1] != to_pos:
                continue
            if is_legal_move(board, mv[0], mv[1], moved_state,
                             turn, en_passant, mv[2]):
                matches.append(mv)

        if not matches:
            print('走子失败')
            continue

        # 升变：多条候选，询问用户
        if len(matches) > 1:
            promotion = _prompt_promotion()
            chosen = next(mv for mv in matches if mv[2] == promotion)
        else:
            chosen = matches[0]

        success, new_en_passant = make_move(
            board, chosen[0], chosen[1], moved_state,
            en_passant=en_passant, promotion=chosen[2],
            pre_validated=True,
        )

        if not success:
            print('走子失败')
            continue

        en_passant = new_en_passant
        turn = _enemy_of(turn)

        # 判断对方状态（只生成一次走法）
        status = game_status(board, turn, moved_state, en_passant)
        if status == 'checkmate':
            print_board(board)
            print(f"{_color_name(turn)}被将死！")
            print(f"{_color_name(_enemy_of(turn))}获胜！")
            break
        if status == 'stalemate':
            print_board(board)
            print(f"{_color_name(turn)}无子可动，和棋！")
            break
        if status == 'check':
            print(f"{_color_name(turn)}被将军！")


if __name__ == '__main__':
    main()