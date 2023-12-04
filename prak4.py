import sqlite3
import time
import sys

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def execute_query(self, query, values=None):
        if values:
            self.cursor.execute(query, values)
        else:
            self.cursor.execute(query)
        self.conn.commit()

    def fetch_one(self, query, values):
        self.cursor.execute(query, values)
        return self.cursor.fetchone()

    def fetch_all(self, query, values):
        self.cursor.execute(query, values)
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close()

class UserDatabase(Database):
    def create_table(self):
        query = '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT,
                nickname TEXT
            )
        '''
        self.execute_query(query)

    def register_user(self, login, password, nickname=None):
        if self.user_exists(login):
            print(f"User '{login}' already exists. Please choose a different username.")
            return

        query = 'INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)'
        try:
            self.execute_query(query, (login, password, nickname))
            print(f"User '{login}' successfully registered.")
        except sqlite3.Error as e:
            print(f"Error registering user '{login}': {e}")

        with open('user_registrations.txt', 'a') as file:
            file.write(f'Username: {login}, Password: {password}, Nickname: {nickname}\n')

    def check_credentials(self, login, password):
        query = 'SELECT * FROM users WHERE username = ? AND password = ?'
        result = self.fetch_one(query, (login, password))
        
        if result:
            print(f"User '{login}' credentials are correct.")
            return True
        else:
            print(f"Invalid credentials for user '{login}'.")
            return False

    def user_exists(self, login):
        query = 'SELECT * FROM users WHERE username = ?'
        result = self.fetch_one(query, (login,))
        return result is not None

    def get_user(self, identifier):
        query = 'SELECT * FROM users WHERE username = ? OR nickname = ?'
        user = self.fetch_one(query, (identifier, identifier))
        if not user:
            return None
        user_info = {
            'id': user[0],
            'username': user[1],
            'password': user[2],
            'nickname': user[3]
        }

        return user_info

    def update_nickname(self, login, new_nickname):
        if login != 'admin':  
            query = 'UPDATE users SET nickname = ? WHERE username = ?'
            try:
                self.execute_query(query, (new_nickname, login))
                print(f"Nickname for user '{login}' has been updated to: {new_nickname}")

                with open('user_registrations.txt', 'a') as file:
                    file.write(f"Nickname updated: Username: {login}, New Nickname: {new_nickname}\n")
            except sqlite3.Error as e:
                print(f"Error updating nickname for user '{login}': {e}")
        else:
            print("You are not allowed to change the admin's nickname.")
    
    def add_default_admin(self):
        admin_username = 'admin'
        admin_password = 'admin_password'

        if not self.user_exists(admin_username):
            query = 'INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)'
            try:
                self.execute_query(query, (admin_username, admin_password, None))
                print("Default admin added to the database.")
            except sqlite3.Error as e:
                print(f"Error adding default admin: {e}")

            with open('user_registrations.txt', 'a') as file:
                file.write(f'Username: {admin_username}, Password: {admin_password}, Nickname: None\n')

class ItemDatabase(Database):
    def create_table(self):
        query = '''
            CREATE TABLE IF NOT EXISTS item_counts (
                item_id INTEGER UNIQUE,
                count INTEGER,
                FOREIGN KEY (item_id) REFERENCES items(id)
            )
        '''
        self.execute_query(query)


    def add_item_count(self, item_id, count):
        query = '''
            INSERT INTO item_counts (item_id, count)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM item_counts WHERE item_id = ?
            )
        '''
        try:
            self.execute_query(query, (item_id, count, item_id))
            print(f"Item count for Item ID {item_id} has been successfully added.")
        except sqlite3.Error as e:
            print(f"Error when adding item count: {e}")

    def update_item_count(self, item_id, count):
        query = 'UPDATE item_counts SET count = ? WHERE item_id = ?'
        try:
            self.execute_query(query, (count, item_id))
            print(f"Item count for Item ID {item_id} has been updated to: {count}")
        except sqlite3.Error as e:
            print(f"Error updating item count for Item ID {item_id}: {e}")

    def get_item_count(self, item_id):
        query = 'SELECT count FROM item_counts WHERE item_id = ?'
        result = self.fetch_one(query, (item_id,))
        if result:
            return result[0]
        else:
            print(f"No item count found for Item ID {item_id}.")
            return None
        
    def get_all_item_counts(self):
        query = 'SELECT item_id, count FROM item_counts'
        return self.fetch_all(query, ())



class OrderDatabase(Database):
    def create_table(self):
        query = '''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT,
                subsection TEXT,
                item INTEGER,
                status TEXT DEFAULT 'Placed',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''
        self.execute_query(query)

    def update_order_status(self, order_id, status):
        query = 'UPDATE orders SET status = ? WHERE id = ?'
        try:
            self.execute_query(query, (status, order_id))
            print(f"Order {order_id} status updated to: {status}")
        except sqlite3.Error as e:
            print(f"Error updating order status for order {order_id}: {e}")

    def get_all_orders(self):
        query = 'SELECT id, timestamp, status FROM orders'
        return self.fetch_all(query, ())
    
class DeliveryDatabase(Database):
    def create_table(self):
        query = '''
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER UNIQUE,
                requires_delivery BOOLEAN DEFAULT 0,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        '''
        self.execute_query(query)

    def add_delivery_status(self, order_id, requires_delivery):
        query_check = 'SELECT * FROM deliveries WHERE order_id = ?'
        existing_record = self.fetch_one(query_check, (order_id,))

        if existing_record:
            print(f"Delivery status for Order ID {order_id} already exists. Updating status.")
            self.update_delivery_status(order_id, requires_delivery)
        else:
            query = 'INSERT INTO deliveries (order_id, requires_delivery) VALUES (?, ?)'
            try:
                self.execute_query(query, (order_id, requires_delivery))
                print(f"Delivery status for Order ID {order_id} has been successfully added.")
            except sqlite3.Error as e:
                print(f"Error when adding delivery status:")
                
    def update_delivery_status(self, order_id, requires_delivery):
        query = 'UPDATE deliveries SET requires_delivery = ? WHERE order_id = ?'
        try:
            self.execute_query(query, (requires_delivery, order_id))
            print(f"Delivery status for Order ID {order_id} has been updated.")
        except sqlite3.Error as e:
            print(f"Error when updating delivery status: {e}")

            
class LogIn:
    def __init__(self, user_db):
        self.user_db = user_db

    def log_in(self):
        while True:
            print("Welcome to our website!")
            menu = input("Select the menu item: \n1. Log in \n2. Log in as an admin \n3. Register \n4. Exit \n:")

            if menu == '1':
                login = input('Username: ')
                password = input('Password: ')

                if self.user_db.check_credentials(login, password):
                    print('You are logged into the "American Pizza" ordering system')
                    time.sleep(1)
                    return login
                else:
                    print('Invalid user credentials. Returning to the menu...')

            if menu == '2':
                while True:
                    admin_username = 'admin'
                    admin_password = 'admin_password'

                    login = input('Admin Username: ')
                    password = input('Admin Password: ')

                    if login == admin_username and password == admin_password:
                        print('You are logged in as an Admin.')
                        time.sleep(1)
                        return login
                    else:
                        print('Invalid admin credentials. Returning to the menu...')
                        break

            elif menu == '3':
                login = input('Enter your Username: ')
                password = input('Enter your Password: ')
                password_repeat = input('Enter your Password again: ')

                if password != password_repeat:
                    print('Passwords are different!')
                    continue

                self.user_db.register_user(login, password)
                print()

            elif menu == '4':
                print('We are waiting for you again on our website!')
                sys.exit()

class Welcome:
    def __init__(self, order_db, user_db, item_db, delivery_db):
        self.order_db = order_db
        self.user_db = user_db
        self.item_db = item_db
        self.delivery_db = delivery_db
        self.is_admin = False

    def welcome(self, login):
        user = self.user_db.get_user(login)
        if user and user['nickname']:
            identifier = user['nickname']
        else:
            identifier = login

        if login == 'admin':
            self.is_admin = True
            while True:
                admin_menu = input("Welcome Admin! What would you like to do?\n"
                                "1. View all orders\n"
                                "2. View item counts\n"
                                "3. Exit\n"
                                "Enter your choice: ")

                if admin_menu == '1':
                    orders = self.order_db.get_all_orders()
                    print("All orders:")
                    for order in orders:
                        print(f"Order {order[0]} generated {order[1]}, Status: {order[2]}")
                elif admin_menu == '2':
                    print("Item Counts:")
                    item_counts = self.item_db.get_all_item_counts()
                    for item in item_counts:
                        print(f"Item ID: {item[0]}, Count: {item[1]}")
                elif admin_menu == '3':
                    print("Exiting Admin menu.")
                    break
                else:
                    print("Invalid choice. Please enter a valid option.")

        else:
            print(f"Hello, {identifier}! Welcome to \"American Pizza\"")

            while True:
                choice = input("You can choose something from this section:\n"
                            "1. Pizza \n2. Sauces \n3. Snacks \n4. Desserts \n5. Drinks \n:")
                if choice.isdigit():
                    choice = int(choice)

                    if 1 <= choice <= 5:
                        sections = {
                            1: 'Pizza',
                            2: 'Sauces',
                            3: 'Snacks',
                            4: 'Desserts',
                            5: 'Drinks'
                        }

                        section = sections[choice]
                        print(f"You have selected a section '{section}' ")

                        subsection_map = {
                            1: {'Pepperoni', 'Teriyaki-Chicken', 'Four cheeses', 'Meat'},
                            2: {'Chile', 'Barbecue', 'Garlic'},
                            3: {'French fry', 'Dodster', 'Nuggets', 'Sandwich'},
                            4: {'Donat', 'Cheesecake'},
                            5: {'Coka-cola', 'Water', 'Fanta'}
                        }

                        print(f"Choose {section[:-1]}:")
                        for idx, subsection in enumerate(subsection_map[choice], start=1):
                            print(f"    {idx}. {subsection}")

                        choice2 = input(": ")

                        if choice2.isdigit():
                            choice2 = int(choice2)

                            if 1 <= choice2 <= len(subsection_map[choice]):
                                subsection_choice = list(subsection_map[choice])[choice2 - 1]
                                print(f"You've selected: {subsection_choice}")

                                while True:
                                    more = input("Anything else? (yes/no): ")

                                    if more.lower() == 'yes':
                                        print("Choose again")
                                        break
                                    elif more.lower() == 'no':
                                        try:
                                            order_id = None
                                            confirm_order = input("Confirm your order (yes/no): ")
                                            if confirm_order.lower() == 'yes':
                                                requires_delivery = input("Do you require delivery? (yes/no): ")
                                                if requires_delivery.lower() == 'yes':
                                                    self.order_db.execute_query("INSERT INTO orders (section, subsection, item, status) VALUES (?, ?, ?, ?)",
                                                                            (section, subsection_choice, choice2, 'Completed'))
                                                    order_id = self.order_db.fetch_one("SELECT id FROM orders ORDER BY id DESC LIMIT 1", ())[0]
                                                    self.delivery_db.add_delivery_status(order_id, True)
                                                    print("The delivery has been successfully completed.")
                                                    return
                                                elif confirm_order.lower() == 'no':
                                                    print("You have chosen pickup")
                                                    return
                                                else:
                                                    print ("Invalid input. Please enter 'yes' or 'no'.")
                                            elif confirm_order.lower() == 'no':
                                                result = self.order_db.fetch_one("SELECT id FROM orders ORDER BY id DESC LIMIT 1", ())
                                                if result is not None:
                                                    order_id = result[0]
                                                self.delivery_db.add_delivery_status(order_id, False)
                                                self.order_db.execute_query("INSERT INTO orders (section, subsection, item, status) VALUES (?, ?, ?, ?)",
                                                                            (section, subsection_choice, choice2, 'Deleted'))
                                                print("Order canceled, stored in the database as deleted.")
                                                return
                                            else:
                                                print("Invalid input. Please enter 'yes' or 'no'.")
                                        except Exception as e:
                                            print(f"An error occurred while processing the order: {e}")
                                            return
                                    else:
                                        print("I didn't understand you, please repeat")
                        else:
                            print("Enter a number within the range")
                    else:
                        print("Enter a valid number")

def main():
    with open('user_registrations.txt', 'w') as file:
        admin_username = 'admin'
        admin_password = 'admin_password'
        file.write(f'Username: {admin_username}, Password: {admin_password}, Nickname: None\n')

    user_db = UserDatabase('database.db')
    user_db.create_table()
    user_db.add_default_admin()

    order_db = OrderDatabase('database.db')
    order_db.create_table()

    item_db = ItemDatabase('database.db') 
    item_db.create_table()
    item_db.add_item_count(1, 50)
    item_db.add_item_count(2, 40)
    item_db.add_item_count(3, 60)
    item_db.add_item_count(4, 20)
    item_db.add_item_count(5, 14)
    item_db.add_item_count(6, 20)
    item_db.add_item_count(7, 11)
    item_db.add_item_count(8, 58)
    item_db.add_item_count(9, 24)
    item_db.add_item_count(10, 30)
    item_db.add_item_count(11, 18)
    item_db.add_item_count(12, 17)
    item_db.add_item_count(13, 9)
    item_db.add_item_count(14, 104)
    item_db.add_item_count(15, 342)
    item_db.add_item_count(16, 98)



    delivery_db = DeliveryDatabase('database.db')
    delivery_db.create_table()

    log_in = LogIn(user_db)
    username = log_in.log_in()

    welcome = Welcome(order_db, user_db, item_db, delivery_db)  
    welcome.welcome(username)

    if username != 'admin':
        while True:
            choice = input("Would you like to set/change your nickname? (yes/no): ")
            if choice.lower() == 'yes':
                new_nickname = input("Enter your new nickname: ")
                
                user_db.update_nickname(username, new_nickname)
                print(f"Your nickname has been updated to: {new_nickname}")
                break
            elif choice.lower() == 'no':
                print("Okay, maybe next time!")
                break
            else:
                print("Invalid input. Please enter 'yes' or 'no'.")
                continue

if __name__ == "__main__":
    main()