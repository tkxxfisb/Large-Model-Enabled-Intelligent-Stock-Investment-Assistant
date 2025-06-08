import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import Logger
import sqlite3

class DatabaseManager:
    def __init__(self, db_name='./stock_assistant.db'):
        
        self.logger = Logger("DatabaseManager")
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        
    
    def create_tables(self):
        # 创建用户表，增加了 funds 字段用于存储用户资金
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                uid TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                funds REAL NOT NULL,
                hashed_password TEXT NOT NULL
            )
        ''')
        # 创建交易记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT,
                action TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (uid) REFERENCES users(uid)
            )
        ''')
        self.conn.commit()
        self.logger.info("数据库建表成功.")

    # 增加用户，可指定初始资金
    def add_user(self, username: str, uid: str, funds: float, hashed_password: str) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO users (uid, username, funds, hashed_password) VALUES (?,?,?,?)', (uid, username, funds, hashed_password))
            
            self.conn.commit()
            self.logger.info(f"用户 {username} 添加成功.")
            return True
    
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"添加用户 {username} 失败: {str(e)}")
            return False
    

    # 增加交易记录
    def add_transaction(self, uid, action, stock_code, quantity, price):
        data = {'success':False, 'message':"操作失败: 未知错误。"}

        if action == '买入':
            cost = quantity * price
            # 查询用户当前资金
            result = self.get_user_funds(uid)
            if result:
                current_funds = result
                if current_funds < cost:
                    data['message'] = f"操作失败: 余额不足，无法购买股票{stock_code}。"
                    return data
                # 资金充足，执行买入操作，扣除资金
                self.cursor.execute('UPDATE users SET funds = funds -? WHERE uid =?', (cost, uid))
            else:
                data['message'] = "操作失败: 未找到该用户。"
                return data
        elif action == '卖出':
            income = quantity * price
            result = self.get_user_funds(uid)
            if not result:
                data['message'] = "操作失败: 未找到该用户。"
                return data
            current_quantity = self.get_quantity_by_user_id(uid)
            if not current_quantity or current_quantity < quantity:
                data['message'] = f"操作失败: 持仓量不足，无法卖出股票{stock_code}。"
                return data
            self.cursor.execute('UPDATE users SET funds = funds +? WHERE uid =?', (income, uid))

        data['success'] = True
        # 插入交易记录
        self.cursor.execute('''
            INSERT INTO transactions (uid, action, stock_code, quantity, price)
            VALUES (?,?,?,?,?)
        ''', (uid, action, stock_code, quantity, price))
        self.conn.commit()
        self.logger.info("操作成功: 添加交易记录。")
        return data

    # 删除用户
    def delete_user(self, uid):
        # 先删除该用户的所有交易记录
        self.cursor.execute('DELETE FROM transactions WHERE uid =?', (uid,))
        # 再删除用户
        self.cursor.execute('DELETE FROM users WHERE uid =?', (uid,))
        self.conn.commit()

    # 删除交易记录，同时需要回滚资金变动
    def delete_transaction(self, transaction_id):
        self.cursor.execute('SELECT uid, action, quantity, price FROM transactions WHERE id =?', (transaction_id,))
        result = self.cursor.fetchone()
        if result:
            uid, action, quantity, price = result
            if action == '买入':
                cost = quantity * price
                self.cursor.execute('UPDATE users SET funds = funds +? WHERE uid =?', (cost, uid))
            elif action == '卖出':
                income = quantity * price
                self.cursor.execute('UPDATE users SET funds = funds -? WHERE uid =?', (income, uid))
            self.cursor.execute('DELETE FROM transactions WHERE id =?', (transaction_id,))
            self.conn.commit()

    # 修改用户信息，可修改用户名和资金
    def update_user(self, uid, new_username=None, new_funds=None):
        update_values = []
        set_clauses = []

        if new_username is not None:
            set_clauses.append('username =?')
            update_values.append(new_username)
        if new_funds is not None:
            set_clauses.append('funds =?')
            update_values.append(new_funds)

        if not set_clauses:
            return

        set_clause = ', '.join(set_clauses)
        update_values.append(uid)
        query = f'UPDATE users SET {set_clause} WHERE uid =?'
        try:
            self.cursor.execute(query, tuple(update_values))
            self.conn.commit()
        except sqlite3.IntegrityError:
            print(f"用户名 {new_username} 已存在。")

    # 修改交易记录，同时需要重新计算资金变动
    def update_transaction(self, transaction_id, action=None, stock_code=None, quantity=None, price=None):
        self.cursor.execute('SELECT uid, action, quantity, price FROM transactions WHERE id =?', (transaction_id,))
        old_result = self.cursor.fetchone()
        if old_result:
            old_uid, old_action, old_quantity, old_price = old_result
            old_cost = old_quantity * old_price
            if old_action == '买入':
                self.cursor.execute('UPDATE users SET funds = funds +? WHERE uid =?', (old_cost, old_uid))
            elif old_action == '卖出':
                self.cursor.execute('UPDATE users SET funds = funds -? WHERE uid =?', (old_cost, old_uid))

            new_action = action if action is not None else old_action
            new_quantity = quantity if quantity is not None else old_quantity
            new_price = price if price is not None else old_price
            new_cost = new_quantity * new_price

            if new_action == '买入':
                # 查询用户当前资金
                self.cursor.execute('SELECT funds FROM users WHERE uid =?', (old_uid,))
                result = self.cursor.fetchone()
                if result:
                    current_funds = result[0]
                    if current_funds < new_cost:
                        # 回滚之前的资金变动
                        if old_action == '买入':
                            self.cursor.execute('UPDATE users SET funds = funds -? WHERE uid =?', (old_cost, old_uid))
                        elif old_action == '卖出':
                            self.cursor.execute('UPDATE users SET funds = funds +? WHERE uid =?', (old_cost, old_uid))
                        return "不能操作: 资金不足，无法完成修改后的买入交易。"
                    # 资金充足，执行买入操作，扣除资金
                    self.cursor.execute('UPDATE users SET funds = funds -? WHERE uid =?', (new_cost, old_uid))
                else:
                    # 回滚之前的资金变动
                    if old_action == '买入':
                        self.cursor.execute('UPDATE users SET funds = funds -? WHERE uid =?', (old_cost, old_uid))
                    elif old_action == '卖出':
                        self.cursor.execute('UPDATE users SET funds = funds +? WHERE uid =?', (old_cost, old_uid))
                    return "不能操作: 未找到该用户。"
            elif new_action == '卖出':
                income = new_quantity * new_price
                self.cursor.execute('UPDATE users SET funds = funds +? WHERE uid =?', (income, old_uid))

            update_values = []
            set_clauses = []

            if action is not None:
                set_clauses.append('action =?')
                update_values.append(action)
            if stock_code is not None:
                set_clauses.append('stock_code =?')
                update_values.append(stock_code)
            if quantity is not None:
                set_clauses.append('quantity =?')
                update_values.append(quantity)
            if price is not None:
                set_clauses.append('price =?')
                update_values.append(price)

            if set_clauses:
                set_clause = ', '.join(set_clauses)
                update_values.append(transaction_id)
                query = f'UPDATE transactions SET {set_clause} WHERE id =?'
                self.cursor.execute(query, tuple(update_values))

            self.conn.commit()
            return self.cursor.lastrowid

    # 查询所有用户
    def get_all_users(self):
        self.cursor.execute('SELECT * FROM users')
        return self.cursor.fetchall()

    # 根据用户 ID 查询用户
    def get_user_by_id(self, uid):
        self.cursor.execute('SELECT * FROM users WHERE uid =?', (uid,))
        return self.cursor.fetchone()

    # 查询所有交易记录
    def get_all_transactions(self):
        self.cursor.execute('SELECT * FROM transactions')
        return self.cursor.fetchall()

    # 根据交易 ID 查询交易记录
    def get_transaction_by_id(self, transaction_id):
        self.cursor.execute('SELECT * FROM transactions WHERE id =?', (transaction_id,))
        return self.cursor.fetchone()

    # 根据用户 ID 查询该用户的所有交易记录
    def get_transactions_by_user_id(self, uid):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM transactions WHERE uid =?', (uid,))
            return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"查询用户 {uid} 的交易记录失败: {str(e)}")
            return []
    
    def get_quantity_by_user_id(self, uid):
        self.cursor.execute('SELECT quantity FROM transactions WHERE uid =? ORDER BY id DESC LIMIT 1', (uid,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return None
    
    def get_user_funds(self, uid):
        self.cursor.execute('SELECT funds FROM users WHERE uid =?', (uid,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_user_by_username(self, username):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username =?', (username,))
            return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"查询用户 {username} 失败: {str(e)}")
    
    def get_user_by_uid(self, uid) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM users WHERE uid =?', (uid,))
            return cursor.fetchone() is not None  # 存在返回 True，否则 False
        except Exception as e:
            self.logger.error(f"查询用户 {uid} 失败: {str(e)}")
            return False
    
    def get_user_positions(self, uid: str) -> list:
        """计算用户当前持仓（基于交易记录），返回包含code、name、quantity、price的列表"""
        from api.stock_api import StockAPI  # 动态导入避免循环依赖
        stock_api = StockAPI()
        
        transactions = self.get_transactions_by_user_id(uid)
        positions = {}  # 键：stock_code，值：{quantity: 持仓量, price: 最后一次交易价格}
        
        for trans in transactions:
            # 交易记录字段顺序：id, uid, action, stock_code, quantity, price
            stock_code = trans[3]
            action = trans[2]
            quantity = trans[4]
            price = trans[5]  # 提取交易价格
            
            # 初始化持仓记录（记录最后一次交易价格）
            if stock_code not in positions:
                positions[stock_code] = {'quantity': 0, 'price': price}
            
            # 根据交易类型更新持仓量
            if action == '买入':
                positions[stock_code]['quantity'] += quantity
                positions[stock_code]['price'] = price  # 买入时更新为最新交易价格
            elif action == '卖出':
                positions[stock_code]['quantity'] -= quantity  # 卖出时不更新交易价格（保持成本价）
        
        # 过滤持仓量>0的股票，并补充股票名称和当前价格
        result = []
        for stock_code, pos in positions.items():
            if pos['quantity'] > 0:
                stock_info = stock_api.get_stock_info_by_code(stock_code)
                if stock_info:  # 避免无名称的股票（如异常数据）
                    result.append({
                        "code": stock_code,
                        "name": stock_info["name"],
                        "quantity": pos["quantity"],
                        "price": stock_info["price"]  # 修改为获取实时价格
                    })
        
        return result


    def close(self):
        self.conn.close()

if __name__ == '__main__':
    db = DatabaseManager()
    db.add_user(username="tongk", uid=1)
    
    
    
