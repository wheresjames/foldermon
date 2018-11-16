
// Create a shortened path string
function makeDisplayPath(path, max, sep = '/', rm = '...')
{
    if (path.length <= max)
        return path;

    p = path.split(sep);
    if (!p.length)
        return path.slice(0, max - rm.length) + rm;

    var ml = p.length;
    while (path.length > max)
    {
        if (0 > ml--)
            return path.slice(0, max - rm.length) + rm;

        if (2 >= p.length)
            return p[0].slice(0, max - rm.length) + rm;

        else
        {
            p = p.slice(0, p.length - 2).concat([p[p.length - 1]])
            path = p.slice(0, p.length - 2).concat([rm, p[p.length - 1]]).join(sep);
        }

    }

    return path;
}

// Constantly refresh files
xx.pmsg('pollfiles', -5000, 'cmdGetFiles', {}, function(ok, d)
{
    if (!$('#pgExists_Folder').length)
        return false;

    if (!ok)
    {
        showMessage(d['error'] ? d['error'] : JSON.stringify(d), '#800');
        return true;
    }

    // Separate files from directories
    var files = [], dirs = [];
    $.each(d['files'], function(k, v)
    {
        if (v['isdir'])
            dirs.push(v);
        else
            files.push(v);
    });

    // Split the path
    path = d['path'] ? d['path'].split('/') : [''];
    if (!path.length || path[0].length)
        path.unshift('');

    pall = '';
    pdata = [];
    $.each(path, function(k, v)
    {   pall = [pall, v].join('/');
        pdata.push({'name': k ? v : makeDisplayPath(d['absroot'], 32), 'fullname': k ? v : d['absroot'], 'path': pall});
    });

    // Sort
    files.sort(function(a, b){ return a.name.localeCompare(b.name); });
    dirs.sort(function(a, b){ return a.name.localeCompare(b.name); });

    // Add folder up path
    if (1 < path.length)
        dirs.unshift({'name': '..', 'isdir': true, 'path': path.slice(0, path.length - 1).join('/')});

    //--------------------------------------------------------------
    // Update the path control

    var selPath = d3.select("#folder_path")
      .selectAll("button")
        .data(pdata);

    selPath.enter()
            .append("button")
              .attr('class', 'btn btn-primary path-button')
              .text(function(d){return d.name})
              .attr('title', d['fullname'])
              .attr('data-toggle', 'tooltip')
              .on('click', function(d)
              {
                  if (d['path'])
                      xx.modify_pmsg('pollfiles', {'params': {'path': d['path']}}, true);
                  else
                      xx.modify_pmsg('pollfiles', {'params': {'path': ''}}, true);
              });

    selPath
        .text(function(d){return d.name});

    selPath.exit()
        .remove();


    //--------------------------------------------------------------
    // Update the tree

    var selTree = d3.select("#folder_tree")
      .selectAll("button")
        .data(dirs, function(d){ return d.name; });

    selTree.enter()
        .append("button")
          .attr('class', 'btn btn-secondary tree-button text-left')
          .style('opacity', function(d){ return ('.' != d.name[0] || '.' == d.name[1]) ? 1.0 : 0.5; })
          .html(function(d){return '<i class="fa fa-folder fa-lg"></i>&nbsp;' + d.name})
          .on('click', function(d)
          {
              if (d['isdir'])
                  if (d['path'])
                      xx.modify_pmsg('pollfiles', {'params': {'path': d['path']}}, true);
                  else
                      xx.modify_pmsg('pollfiles', {'params': {'path': path.concat([d['name']]).join('/')}}, true);
          });

    selTree.exit()
        .remove();

    //--------------------------------------------------------------
    // Update the list

    var selList = d3.select("#folder_list")
      .selectAll("button")
        .data(files, function(d){ return d.name; });

    selList.enter()
        .append("button")
          .attr('class', 'btn btn-secondary list-button text-left')
          .style('opacity', function(d){ return ('.' != d.name[0] || '.' == d.name[1]) ? 1.0 : 0.5; })
          .html(function(d){return '<i class="fa fa-file fa-lg"></i>&nbsp;' + d.name})
          .on('click', function(d)
          {
              if (d['link'])
                  location.replace(d['link']);
          });

    selList.exit()
        .remove();

    return true;
});

