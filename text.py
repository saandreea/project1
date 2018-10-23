dict = {"isbn": [1,2,3,4], "title": ['a', 'b', 'c', 'd']}

print(dict['isbn'][0])

dict['isbn'].append(5)
print(dict['isbn'])

print(len(dict['isbn']))


from datetime import  date

now = date.today()


print(now)
print(type(now))
