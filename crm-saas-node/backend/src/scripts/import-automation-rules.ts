import path from 'path';
import { RuleImporter } from '../services/automation/RuleImporter';

async function main() {
  const importer = new RuleImporter();
  const rulesDir = path.join(__dirname, '../../../automation-rules');
  
  console.log('Importing automation rules from:', rulesDir);
  
  try {
    await importer.importRulesFromDirectory(rulesDir);
    console.log('✅ Import complete');
    process.exit(0);
  } catch (error) {
    console.error('Import failed:', error);
    process.exit(1);
  }
}

main();
