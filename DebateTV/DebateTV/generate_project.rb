require 'rubygems'
gem 'xcodeproj'
require 'xcodeproj'

project_name = 'DebateTVAIDebateArena'
project = Xcodeproj::Project.new("#{project_name}.xcodeproj")

target = project.new_target(:application, project_name, :ios, '17.0')
target.build_configuration_list.set_setting('INFOPLIST_KEY_UIApplicationSceneManifest_Generation', 'YES')
target.build_configuration_list.set_setting('GENERATE_INFOPLIST_FILE', 'YES')
target.build_configuration_list.set_setting('INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents', 'YES')
target.build_configuration_list.set_setting('INFOPLIST_KEY_UILaunchScreen_Generation', 'YES')
target.build_configuration_list.set_setting('INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone', 'UIInterfaceOrientationPortrait')
target.build_configuration_list.set_setting('PRODUCT_BUNDLE_IDENTIFIER', "com.example.#{project_name}")
target.build_configuration_list.set_setting('MARKETING_VERSION', '1.0')
target.build_configuration_list.set_setting('CURRENT_PROJECT_VERSION', '1')

app_group = project.main_group.new_group('App', 'Sources/App')

Dir.glob('Sources/App/*').each do |path|
  next if File.directory?(path) && !path.end_with?('.xcassets')
  file_ref = app_group.new_file(File.basename(path))
  target.add_file_references([file_ref])
end

project.save
puts "Successfully created #{project_name}.xcodeproj"
