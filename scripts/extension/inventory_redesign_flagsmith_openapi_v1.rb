require 'yaml'
require 'json'
require 'digest'
require 'fileutils'
root=File.expand_path('../..',__dir__)
source=File.join(root,'results/redesign-evaluation-source-wave2-v1/1.txt')
x=YAML.safe_load(File.read(source),permitted_classes: [],permitted_symbols: [],aliases: false)
rows=x.fetch('paths').sort.flat_map do |path,methods|
 methods.select{|method,op|method=='post'}.map do |method,op|
  {path:path,method:method.upcase,operation_id:op['operationId'],description:op['description'],request_body:op['requestBody'],responses:op['responses'],source_eligibility:'unassessed'}
 end
end
out=File.join(root,'results/redesign-evaluation-flagsmith-inventory-v1')
FileUtils.mkdir_p(out)
File.write(File.join(out,'inventory.json'),JSON.pretty_generate({kind:'original_advertised_post_inventory_not_eligibility_selection',source_sha256:Digest::SHA256.file(source).hexdigest,openapi:x['openapi'],paths:x['paths'].length,rows:rows})+"\n")
puts JSON.generate({paths:x['paths'].length,post_operations:rows.length,selected_workflows:0})
