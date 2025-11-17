if __name__ == '__main__':
    config = {}
    execfile('awapSettings.conf', config)

    print 'fieldTags = ',config['fieldTags']
    print 'fieldTagsToDirName = ',config['fieldTagsToDirName']
