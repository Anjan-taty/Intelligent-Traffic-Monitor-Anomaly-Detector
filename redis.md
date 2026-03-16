### Redis:

#### What is redis?
- Redis (Remote Dictionary Server) is a high-speed, open-source in-memory data structure store. While a standard database (like the PostgreSQL one you've been using) stores data on your SSD, Redis keeps everything in your RAM for near-instant access.


#### Will storage be stored?
1. If Persistence is OFF: Yes, you will lose all data because it only exists in the RAM.
2. If Persistence is ON: No, Redis will reload your data from a file on your disk (SSD/HDD) when it restarts.

#### Manual way (Foreground Process)
- sudo systemctl start redis-server ->for starting if already installed
- sudo systemctl stop redis-server ->for stopping it
- sudo systemctl restart redis-server ->for restarting it

#### Automatic (Background Process)
- sudo systemctl enable redis-server ->For starting automatically in background
- sudo systemctl disable redis-server ->for stopping it.

#### Additional info:
- It is case insensitive so capital or small for commands it does not matter.
- Everything stored in the redis is stored in the string format.


#### For storing things
redis-cli ->For starting cli thing. Terminal will open
- SET <key> <value> ->For storing values
- GET <key> ->For getting the value, we get the value.
- DEL <key> ->Deletes that key,value pair.
- EXISTS <key> ->Gives 1 if it is present in redis otherwise 0.
- KEYS * ->Gives all the keys present in the redis.
- FLUSHALL ->Removes everything from the redis.
- TTL <key> ->Gives how much time that key is going to live.(Time to expire)
- EXPIRE <key> <duration_in_seconds> ->That keys now expires after that time runs out
- SETEX <key> <duration_in_seconds> <value> ->This value is set a timer at the time of creation only.
Note:see in setex first key them ttl not its value.

#For Arrays or lists.
- lpush <list_name> <item_name> ->puts item to the left of the list and if the list is not there then it creates it.
- rpush <list_name> <item_name> ->puts item to the right of the list
- lpop <list_name> <item_name> ->pops item from the left of the list and returns to us
- rpop <list_name> <item_name> ->pops item from the right of the list and returns to us
- lrange <list_name> <starting_index> <ending_index> ->Returns us all the items in the list in the mentioned range of indices.

#For sets(Unique lists which does not have duplicates)
- sadd <set_name> <"item1,item2"> ->Adds items to sets. if duplicates are there then it returns 0 as it could not do that.(sets add)
- srem <set_name> <item1> ->Removes item1 from set. If faced any error then it returns 0.
- smembers <set_name> ->Gives all the items in the set

#For Hashing:(For every command we prefix with the H letter)
- HSET <variable_name> <key> <value> ->Sets value
- HGET <variable_name> <key> ->Gets the value for the key
- HGETALL <variable_name> ->Gets all keys and values of that variable
- HDEL <variable_name> <key> ->Only that key and value associated to that variable gets deleted
