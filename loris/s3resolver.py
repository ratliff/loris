# -*- coding: utf-8 -*-
from loris.resolver import _AbstractResolver
from urllib import unquote
import urlparse
from os.path import join, exists
import boto3
import botocore
import logging

logger = logging.getLogger('webapp')


class S3Resolver(_AbstractResolver):
    '''
    Resolver for images coming from AWS S3 bucket.
    The config dictionary MUST contain
     * `cache_root`, which is the absolute path to the directory where source images
        should be cached.
     * `source_root`, the s3 root for source images.
    '''
    def __init__(self, config):
        ''' setup object and validate '''
        super(S3Resolver, self).__init__(config)
        self.cache_root = self.config.get('cache_root')
        source_root = self.config.get('source_root')
        assert source_root, 'please set SOURCE_ROOT in environment'
        scheme, self.s3bucket, self.prefix, ___, ___ = urlparse.urlsplit(
            source_root
        )
        assert scheme == 's3', '{0} not an s3 url'.format(source_root)


    def is_resolvable(self, ident):
        '''does this file even exist?'''
        ident = unquote(ident)
        local_fp = join(self.cache_root, ident)
        if exists(local_fp):
            return True
        else:
            # check that we can get to this object on S3
            s3 = boto3.resource('s3')

            try:
                # Strip off everything in the URL after the filename
                key = ident
                logger.debug('Checking existence of Bucket = %s   Filename = %s', self.s3bucket, key)
                s3.Object(self.s3bucket, key).load()
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    logger.debug('Check for file returned HTTP CODE = 404')
                    return False

            logger.debug('is_resolvable = True')
            return True


    def resolve(self, ident):
        '''get me the file'''
        ident = unquote(ident)
        local_fp = join(self.cache_root, ident)
        logger.debug('local_fp: %s' % (local_fp))

        if exists(local_fp):
            format = 'jp2' # FIXME
            logger.debug('src image from local disk: %s' % (local_fp,))
            return (local_fp, format)
        else:
            # get image from S3
            bucketname = self.s3bucket
            key = ident.partition('/')[0]
            logger.debug('Getting img from AWS S3. bucketname, key: %s, %s' % (bucketname, key))
            s3_client = boto3.client('s3')
            s3_client.download_file(bucketname, key, local_fp)

            format = 'jp2' #FIXME
            logger.debug('src format %s' % (format,))

            return (local_fp, format)

