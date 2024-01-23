def readCSV(file):
    import csv
    result = []
    with open(file, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter='\n')
        for row in reader:
            result.append(row)
    return result


def createExpiryDate(expireOffset = 1800):
    from time import time
    return int(time() + expireOffset)