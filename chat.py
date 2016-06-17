# Checklist for each function
#
# Test cases for Sprint
#
# OK Help
# OK Time
# OK Date
# New user:
#  OK create
#  OK user already exist
# login:
#  OK logs in
#  OK no user found
#
# Chatgroup:
#   OK create group
#   OK join group
#   OK send message to group
#

from flask import Flask
from flask_sockets import Sockets
import datetime
import MySQLdb

app = Flask(__name__)
app.debug = True
sockets = Sockets(app)

db = MySQLdb.connect("us-cdbr-iron-east-04.cleardb.net",
                     "b44fb6baf27ee4",
                     "34ddc169",
                     "heroku_3ec1d9057622ed5")
cursor = db.cursor()
cursor.execute("SELECT VERSION()")
version = cursor.fetchone()
print("Database version: ", version)

#list for bots connecting to server
bots = set()
#lists
todo = {}
helpCommandsBot = {
    "bot ping":"returns pong",
    "bot todo add <command> <data>":"adds new command and data into doto list",
    "bot todo delete <command>":"delete command and corresponding data from todo list",
    "bot todo list":"returns a list of commands/data. if no data, return todo empty",
    "bot help":"you know how to use this if you are reading this"

}
helpCommandsOriginal = {
    "bot date":"returns the date and time",
    "bot time":"returns time",
    "bot newuser <username> <password>":"create new user",
    "bot login <username> <password>":"log into your account",
    "bot close":"close the connection",
    "bot help":"you know how to use this if you are reading this"

}
helpCommandsGroupChat = {
    "chat newuser <username> <password>":"create new user",
    "chat login <username> <password>":"log into your account",
    "chat create <groupname> <password>":"create new group",
    "chat join <groupname> <password>":"join existing group",
    "chat <groupname> <message>":"send message to the group if you are in it",
    "chat close":"close the connection",
    "chat help":"you know how to use this if you are reading this"
}

cursor = db.cursor()
def sql_exec(cmd, params=None):
    try:
        cursor.execute(cmd, params)
        db.commit()
    except:
        db.rollback()

def is_empty(any_structure):
    if any_structure:
        print('Structure is not empty.')
        return False
    else:
        print('Structure is empty.')
        return True


# send to all bots connected to server
def send_data(data):
    print("SENDING:");
    print('{"data": "'+data+'"}')
    try:
        for bot in bots:
            if not bot.closed:
                bot.send('{"data": "'+data+'"}')
    except websockets.exceptions.ConnectionClosed:
        print("Couldn't send")


#functions for test cases
@sockets.route('/bot')
def echo_socket(ws):
    bots.add(ws)
    while not ws.closed:
        print("Receiving...")
        message = ws.receive()
        if message == None:
            print("No message received :(")
            return
        print("Message: ", message)
        send_data(message) #send back message to everyone
        # ping pong case
        if message == "bot ping":
            send_data("pong")
            ws.close()
        elif message == "bot help":
            helpmessage = ""
            for k,v in helpCommandsBot.items():
                helpmessage += k + " - " + v + "\n"
            ws.send(helpmessage)
        # todo list commands
        elif message.startswith("bot todo"):
            parts = message.split(" ",5);
            action = parts[2] #add,delete,list
            #add command/data to list
            if action == "add":
                key = parts[3]
                value = parts[4]
                todo[key] = value
                send_data("todo added")
            # delete a command from list
            elif action =="delete":
                key = parts[3]
                del todo[key]
                send_data("todo deleted")
            #return the complete list
            elif action == "list":
                if len(todo) == 0:
                    send_data("todo empty")
                else:
                    data = ""
                    for k,v in todo.items():
                        data += k + " " + v + "\\n"
                    send_data(data[:-2])
        else:
            print("Unknown command")
    bots.remove(ws)
    print("Closed")

#original Commands
@sockets.route('/original')
def additional_commands(ws):
    print("Additional commands running")
    #bots.add(ws)
    while not ws.closed:
        print("Receiving chat commands...")
        message = ws.receive()
        if (message == None or message == "bot close"):
            print("No message received :(")
            ws.send("Connection closed")
            ws.close()
            return
        # return current time
        if message == "bot date":
            time = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
            ws.send(time)
        elif message == "bot time":
            time = datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S')
            ws.send(time)

        # list available commands
        elif message == "bot help":
            helpmessage = ""
            for k,v in helpCommandsOriginal.items():
                helpmessage += k + " - " + v + "\n"
            ws.send(helpmessage)
        # create new user or login
        elif (message.startswith("bot newuser")): # username password
            parts = message.split(" ",4);
            password = parts[3]
            username = parts[2]
            c = db.cursor()
            c.execute("SELECT * FROM user WHERE username = %s;", (username,) )
            userExist = c.fetchall()
            #if given username doesnt exist
            if is_empty(userExist) == True:
                sql_exec("INSERT INTO user (ws, username, password) VALUES (%s,%s,PASSWORD(%s))", (ws,username,password) );
                ws.send('New User Created\n Hello '+ username)
            # if given username is already in list
            else:
                ws.send('username already taken')
        elif message.startswith("bot login"):
            parts = message.split(" ",4);
            password = parts[3]
            username = parts[2]
            c = db.cursor()
            c.execute("SELECT * FROM user WHERE username = %s and password=PASSWORD(%s);", (username,password) )
            userExist = c.fetchall()
            if is_empty(userExist) == True:
                ws.send("user or password not correct")
            # if given username is already in list
            else:
                sql_exec("UPDATE user SET ws=%s WHERE username=%s", (ws,username))
                ws.send("Welcome back " + username)

@sockets.route('/groupchat')
def group_chat(ws):
    bots.add(ws)
    while not ws.closed:
        print("Receiving groupchat commands...")
        message = ws.receive()
        print(message)

        if (message == None or message == "chat close"):
            print("No message received :(")
            ws.send("Connection closed")
            ws.close()
            return
        if message == "chat help":
            helpmessage = ""
            for k,v in helpCommandsGroupChat.items():
                helpmessage += k + " - " + v + "\n"
            ws.send(helpmessage)
        #create new group
        elif message.startswith("chat create") : # groupname password
            parts = message.split(" ",4);
            groupname = parts[2]
            password = parts[3]
            c = db.cursor()
            c.execute("SELECT * FROM chatgroup WHERE groupID=%s", (groupname,) )
            groupExist = c.fetchall()
            #group doesnt exist
            if is_empty(groupExist) == True:
                sql_exec("INSERT INTO chatgroup (groupID, password) VALUES (%s,PASSWORD(%s))", (groupname,password) );
                ws.send("Created new group")
            #group exist
            else:
                ws.send("Group name already exist. Your group was not made")
        #join any chat
        elif message.startswith("chat join"):
            parts = message.split(" ",4);
            groupname = parts[2]
            password = parts[3]
            c = db.cursor()
            c.execute("SELECT * FROM chatgroup WHERE groupID=%s and password =PASSWORD(%s)", (groupname,password) )
            groupExist = c.fetchall()
            #group doesnt exist
            if is_empty(groupExist) == True:
                ws.send("No group found. Try again.")
            #group exist
            else:
                print("ws is:",ws)
                cursor = db.cursor()
                cursor.execute("SELECT username FROM user WHERE ws=%s", (ws,))
                userAccount = cursor.fetchone()
                print("Printing out userAccount: ",userAccount)
                if is_empty(userAccount) == True:
                    ws.send("You must be logged in to use chat")
                else:
                    sql_exec("INSERT INTO chat_users (UserID, GroupID) VALUES (%s,%s)", (userAccount,groupname) );
                    temp = "Welcome ", userAccount[0], "You joined into group ", groupname
                    ws.send(userAccount[0], "You joined into group ", groupname)
        elif (message.startswith("chat newuser")): # username password
            parts = message.split(" ",4);
            password = parts[3]
            username = parts[2]
            c = db.cursor()
            c.execute("SELECT * FROM user WHERE username = %s;", (username,) )
            userExist = c.fetchall()
            #if given username doesnt exist
            if is_empty(userExist) == True:
                sql_exec("INSERT INTO user (ws, username, password) VALUES (%s,%s,PASSWORD(%s))", (ws,username,password) );
                ws.send('New User Created\n Hello '+ username)
            # if given username is already in list
            else:
                ws.send('username already taken')
        elif message.startswith("chat login"):
            parts = message.split(" ",4);
            password = parts[3]
            username = parts[2]
            c = db.cursor()
            c.execute("SELECT * FROM user WHERE username = %s and password=PASSWORD(%s);", (username,password) )
            userExist = c.fetchall()
            if is_empty(userExist) == True:
                ws.send("user or password not correct")
            # if given username is already in list
            else:
                sql_exec("UPDATE user SET ws=%s WHERE username=%s", (ws,username))
                ws.send("Welcome back " + username)

        #send message to all groups user is in
        elif message.startswith("chat"):# group content
            parts = message.split(" ",3)
            group = parts[1]
            content = parts[2]
            #get username
            cursor = db.cursor()
            cursor.execute("SELECT username FROM user WHERE ws=%s", (ws,) )
            username = cursor.fetchone()
            if is_empty(username) == True:
                print("you must be logged in")
                ws.send("You must be logged in to chat people")
                break
            else:
                #validate that user is in group
                cursor = db.cursor()
                cursor.execute("SELECT GroupID FROM chat_users WHERE UserID=%s and GroupID= group ",(username[0],group))
                groups = cursor.fetchone()
                if is_empty("groups") == True:
                    print("User doesnt belong in this group")
                    ws.send("You do not belong in this group yet")
                else:
                    #get list of users in the group
                    c = db.cursor()
                    c.execute("SELECT userID FROM chat_users WHERE GroupID = %s",(g,))
                    usersInGroup = fetchall
                    for i in usersInGroup:
                        c = db.cursor()
                        c.execute("SELECT ws FROM user WHERE username = %s",(i,))
                        ws = c.fetchone
                        if is_empty(ws) == False:
                            ws.send(content)

if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
