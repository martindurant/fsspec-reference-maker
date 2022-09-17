import fsspec


def class_factory(func):
    """Experimental uniform API across function-based file scanners"""

    class FunctionWrapper:
        __doc__ = func.__doc__
        __module__ = func.__module__

        def __init__(self, url, storage_options=None, inline_threshold=100, **kwargs):
            self.url = url
            self.storage_options = storage_options
            self.inline = inline_threshold
            self.kwargs = kwargs

        def translate(self):
            return func(
                self.url,
                inline_threshold=self.inline,
                storage_options=self.storage_options,
                **self.kwargs,
            )

        def __str__(self):
            return f"<Single file to zarr processor using {func.__module__}.{func.__qualname__}>"

        __repr__ = __str__

    return FunctionWrapper


def apply_offsets(refs, **storage_options):
    fs = fsspec.filesystem("reference", fo=refs, **storage_options)
    if "tar" in fs.fss:
        target = fs.fss["tar"]
        offsets = {ti.name: (ti.offset_data, ti.size) for ti in target.tar.getmembers()}
    elif "zip" in fs.fss:
        target = fs.fss["zip"]
        offsets = {
            zi.filename: (zi.header_offset + len(zi.FileHeader()), zi.file_size)
            for zi in target.filelist
        }
    else:
        raise NotImplementedError
    remote = target.fs.of.name
    outref = {}
    for key, val in fs.references.items():
        k = target._strip_protocol(key)
        if isinstance(val, (str, bytes)):
            outref[key] = val
        if len(val) == 1:
            outref[k] = [remote] + offsets
        else:
            outref[k] = [remote, val[0] + offsets[0], val[1]]
    return outref
