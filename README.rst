encode-annex
============

Introduction
------------

encode-annex takes a list of encode experiment ids and
pushes them into a git-annex repository with quite
a bit of metadata attached to the files.

Motivation
----------

The current ENCODE Project website tracks a vast array of
useful metadata about experiments that have been submitted.

Back in ENCODE2 they attempted to use the metadata to generate
"filenames". However since the names were being used as mysql
table names there was a modest character limit on the names,
and so the number of characters available for each metadata field
shrank to the point of unusability.

So for ENCODE3 every file gets its own accession ID, which
though is easy to track in a database isn't very friendly
for the end user.

Also the current website lacks any direct way of downloading
all the files for an experiment.

encode-annex takes advantage of a tool `git-annex`_, which
is designed to allow manage files with git, without checking
the file contents into git -- something you want to avoid
when dealing with large files.

Also as one of the big things you want to do with git is 
replicate projects on multiple computers, git-annex includes
the ability to synchronize files between multiple repositories.

And in this case a repository can also mean someone elses website, 
using the ``git annex addurl`` command. 

However manually adding each file and adding all the 
useful metadata hidden in the ENCODE json objects 
would be annoying, so I wrote this to try and make this easier
to do.

Tutorial
========

Imagine you have an experiment you're interested in. `ENCSR000CWQ`_::

    encode-annex.py --init -d comparison ENCSR000CWQ

``--init`` tells encode-annex to initilize the git and git annex
repositories if needed.

``-d`` gives it a target directory, otherwise it defaults to the
current directory.

after a few moments of running you'll end up with a directory tree looking like::
    
    ENCFF000EAX.gtf    ENCFF000EBM.fastq  ENCFF000ECD.gtf     ENCFF000ECS.gtf
    ENCFF000EAZ.gtf    ENCFF000EBN.fastq  ENCFF000ECE.bigBed  ENCFF000ECV.gtf
    ENCFF000EBC.gtf    ENCFF000EBO.fastq  ENCFF000ECF.bigBed  ENCFF000ECX.gtf
    ENCFF000EBE.fastq  ENCFF000EBP.fastq  ENCFF000ECG.bigBed  ENCFF000ECZ.gtf
    ENCFF000EBF.fastq  ENCFF000EBQ.fastq  ENCFF000ECJ.bam     ENCFF000EDB.gtf
    ENCFF000EBG.fastq  ENCFF000EBR.fastq  ENCFF000ECL.bam     ENCFF000EDE.gtf
    ENCFF000EBH.fastq  ENCFF000EBT.gtf    ENCFF000ECM.bam     ENCFF000EDG.gtf
    ENCFF000EBI.fastq  ENCFF000EBU.gtf    ENCFF000ECN.bam     ENCFF000EDH.gtf
    ENCFF000EBJ.fastq  ENCFF000EBW.gtf    ENCFF000ECO.bam     ENCFF000EDJ.bigWig
    ENCFF000EBK.fastq  ENCFF000EBY.gtf    ENCFF000ECP.bam     ENCFF000EDL.bigWig
    ENCFF000EBL.fastq  ENCFF000ECB.gtf    ENCFF000ECQ.gtf     ENCFF000EDM.bigWig

If you look carefully you'll notice all of the files are broken symlinks.

What has happened is git annex has recorded the a placeholder file which is
actually stored at a remote url. You can download files with comands like
``git annex get ENCFF00ECB.gtf`` or ``git annex get *.fastq``

What will hopefully make this much more useful is git-annex's `metadata view`_.

First lets see what metadata has been attached by encode-annex::
    
    git annex metadata ENCFF000EBE.fastq
    metadata ENCFF000EBE.fastq 
        accession=ENCFF000EBE
        accession-lastchanged=2014-10-17@00-32-25
        assay_term_id=OBI:0001271
        assay_term_id-lastchanged=2014-10-17@00-32-25
        assay_term_name=RNA-seq
        assay_term_name-lastchanged=2014-10-17@00-32-25
        biological_replicate_number=1
        biological_replicate_number-lastchanged=2014-10-17@00-32-25
        biosample_term_id=EFO:0001203
        biosample_term_id-lastchanged=2014-10-17@00-32-25
        biosample_term_name=MCF-7
        biosample_term_name-lastchanged=2014-10-17@00-32-25
        biosample_type=immortalized cell line
        biosample_type-lastchanged=2014-10-17@00-32-25
        dataset=/experiments/ENCSR000CWQ/
        dataset-lastchanged=2014-10-17@00-32-25
        date_created=2012-03-23
        date_created-lastchanged=2014-10-17@00-32-25
        dbxrefs=GEO:GSM958745
        dbxrefs=UCSC-ENCODE-hg19:wgEncodeEH001421
        dbxrefs-lastchanged=2014-10-17@00-32-25
        file_format=fastq
        file_format-lastchanged=2014-10-17@00-32-25
        lab=/labs/barbara-wold/
        lab-lastchanged=2014-10-17@00-32-25
        lastchanged=2014-10-17@00-32-25
        output_type=reads
        output_type-lastchanged=2014-10-17@00-32-25
        paired_ended=True
        paired_ended-lastchanged=2014-10-17@00-32-25
        submitted_file_name=hg19/wgEncodeCaltechRnaSeq/wgEncodeCaltechRnaSeqMcf7R2x75Il200FastqRd1Rep1.fastq.tgz.dir/11581_61PKCAAXX_c152_l2_r1.fastq.gz
        submitted_file_name-lastchanged=2014-10-17@00-32-25
        technical_replicate_number=1
        technical_replicate_number-lastchanged=2014-10-17@00-32-25
        uuid=7c423fab-ed70-4f3f-b92a-5735005f53ac
        uuid-lastchanged=2014-10-17@00-32

What git-annex provides is a way to construct views of a repository by quering the 
metadata. For instance::
    
    git annex view biological_replicate_number='*' file_format=fastq

produces a directory tree like this::
    
    1/ENCFF000EBE.fastq
    1/ENCFF000EBG.fastq
    1/ENCFF000EBN.fastq
    1/ENCFF000EBL.fastq
    1/ENCFF000EBF.fastq
    1/ENCFF000EBM.fastq
    2/ENCFF000EBI.fastq
    2/ENCFF000EBP.fastq
    2/ENCFF000EBO.fastq
    2/ENCFF000EBH.fastq
    3/ENCFF000EBK.fastq
    3/ENCFF000EBQ.fastq
    3/ENCFF000EBR.fastq
    3/ENCFF000EBJ.fastq

.. _git-annex: http://git-annex.branchable.com/
.. _ENCSR000CWQ: https://www.encodeproject.org/experiments/ENCSR000CWQ/
.. _metadata view: http://git-annex.branchable.com/tips/metadata_driven_views/
