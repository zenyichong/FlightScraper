# Collects information from user on which route(s) to check and the desired date of travel

import json


def add_trips():
    """
    Collects information from user on which flight routes to check and
    the desired dates of travel. Saves the information in a json format
    to data.json in the same directory.
    """
    try:
        with open('trips.json') as f:
            user_dict = json.load(f)
    except FileNotFoundError:
        user_dict = {}
    flag = input('\nInput user data? [y/n]  ').lower()

    while flag == 'y':
        temp_dict = {}
        name = input('Name: ').title()
        if name in user_dict:
            for el in user_dict[name]:
                for k, v in el.items():
                    print(f'{k}: {v}')
                print()
            temp = input("""
Travel information for user already collected.
[y] to input new trip information
[n] to input trip information for different user
[q] to quit
""").lower()
            if temp == 'y':
                pass
            elif temp == 'n':
                continue
            elif temp == 'q':
                break
        else:
            user_dict[name] = []

        origin = input('\nOrigin Airport(use IATA code eg. PEN): ').upper()
        temp_dict['Origin'] = origin
        dest = input('Destination Airport(use IATA code eg. SIN): ').upper()
        temp_dict['Destination'] = dest
        d_date = input('Date of Departure(in the format DD/MM/YYYY): ')
        temp_dict['Dep_date'] = d_date
        a_date = input('Date of Return(in the format DD/MM/YYYY): ')
        temp_dict['Ret_date'] = a_date
        # roundtrip = input('Roundtrip [y/n]: ').lower()
        # temp_dict['Roundtrip'] = True if roundtrip == 'y' else False
        price = int(
            input('Target price(in MYR) reached to receive email alert: '))
        temp_dict['Target_price'] = price
        email = input('Preferred email to receive alerts: ')
        temp_dict['Email_address'] = email

        user_dict[name].append(temp_dict)
        print(f'\nSaving the following information for {name}...')
        for k, v in temp_dict.items():
            print(f'{k}: {v}')
        print()
        flag = input('Continue collecting data? [y/n]  ').lower()

    with open('trips.json', 'w') as f:
        json.dump(user_dict, f, indent=2)


def remove_trips():
    """
    Allows for the removal of one or more trip(s) from the list of trips associated
    with a particular user.
    """
    try:
        with open('trips.json') as f:
            user_dict = json.load(f)
    except FileNotFoundError:
        print('\nNo user information has been collected yet. Aborting...')
        return

    names = list(user_dict.keys())
    print('\nChoose from the following list of name(s) to delete from')
    print(names)
    name = input('\nTarget name: ').title()
    while name not in names:
        print('Invalid input. Choose a name in the list.\n')
        name = input('\nTarget name: ').title()
    for ind, el in enumerate(user_dict[name]):
        print(f'Index: {ind}')
        print(f"Origin Airport: {el['Origin']}")
        print(f"Destination Airport: {el['Destination']}")
        print(f"Date of Departure: {el['Dep_date']}")
        print(f"Date of Return: {el['Ret_date']}\n")

    num_list = input("""
Choose the index or indices of the trip(s) to be deleted.
If more than one, input the indices as space separated integers.
Eg. 0 2
To cancel any deletions, press x.
""")
    if num_list == 'x':
        return
    try:
        num_list = [int(x) for x in num_list.split()]
    except AttributeError:
        num_list = [int(num_list)]
    temp = []
    for i in range(len(user_dict[name])):
        if i not in num_list:
            try:
                temp.append(user_dict[name])
            except KeyError:
                pass
    if not temp:
        print('No trips remaining for user. Removing user from list...')
        del user_dict[name]
    else:
        print('\nRemaining trips for this user.\n')
        for elem in temp:
            for k, v in elem.items():
                print(f'{k}: {v}')
            print()
        if input('Keep changes? [y/n]  ').lower() == 'y':
            user_dict[name] = temp

    with open('trips.json', 'w') as f:
        json.dump(user_dict, f, indent=2)


def main():
    while True:
        n = input("""
What action would you like to perform?
[1] Add trip(s) for a user
[2] Remove trip(s) from a user's trip list
[q] Quit
""").lower()
        if n == '1':
            add_trips()
        elif n == '2':
            remove_trips()
        elif n == 'q':
            break
        else:
            print('Invalid input. Try again.\n')


if __name__ == '__main__':
    main()
