#変数(板情報)
board_temp = []
board = {'asks': {}, 'bids': {}}

# リアルタイムデータの受信
async def realtime(self, response):

    # 板情報
    if response['channel'] == 'orderbook':
        data = response['data']

        if  data['action'] == 'partial':
            self.board_temp = data
            self.board = self.reformat_board(data)

        elif  data['action'] == 'update':
            if len(self.board) > 0:
                self.board = self.update_board(data, self.board)

        print(self.board)


# ---------------------------------------- #
# データ整形関数
# ---------------------------------------- #
# ストリーミングデータを板情報更新用の辞書データへ整形
def reformat_board(self, data):
    board = {'asks': {}, 'bids': {}}
    for key in data.keys():
        if key == 'bids':
            board[key] = {float(quote[0]): float(quote[1]) for quote in data[key]}

        elif key == 'asks':
            board[key] = {float(quote[0]): float(quote[1]) for quote in data[key]}

    return board

# 板情報を更新
def update_board(self, data, board):
    for key in data.keys():
        if key in ['bids', 'asks']:
            for quote in data[key]:
                price = float(quote[0])
                size = float(quote[1])
                if price in board[key]:
                    if size == 0.0:
                        # delete
                        del board[key][price]
                    else:
                        # update
                        board[key][price] = size
                else:
                    if size > 0.0:
                        # insert
                        board[key].update({price: size})

            # sort
            if key == 'asks':
                board[key] = {key: value for key, value in sorted(board[key].items())}
            elif key == 'bids':
                board[key] = {key: value for key, value in sorted(board[key].items(), key=lambda x: -x[0])}

    return board                 
