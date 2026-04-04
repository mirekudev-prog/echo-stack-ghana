const Database = require('better-sqlite3');
const bcrypt = require('bcryptjs');
const path = require('path');

const dbPath = path.join(__dirname, 'echostack.db');
const db = new Database(dbPath);

async function migratePasswords() {
    console.log('Starting password migration...');

    try {
        // Get all users
        const stmt = db.prepare('SELECT id, password FROM users');
        const rows = stmt.all();

        if (rows.length === 0) {
            console.log('No users found to migrate.');
            return;
        }

        let migratedCount = 0;
        let errorCount = 0;
        const updateStmt = db.prepare('UPDATE users SET password = ? WHERE id = ?');

        for (const user of rows) {
            try {
                // Check if password is already hashed (starts with $2a$, $2b$, or $2y$)
                if (user.password.startsWith('$2')) {
                    console.log(`User ID ${user.id}: Already hashed, skipping.`);
                    continue;
                }

                // Hash the plain-text password
                const saltRounds = 10;
                const hashedPassword = await bcrypt.hash(user.password, saltRounds);

                // Update the database
                updateStmt.run(hashedPassword, user.id);
                console.log(`User ID ${user.id}: Password successfully hashed.`);
                migratedCount++;
            } catch (hashErr) {
                console.error(`Error hashing password for user ${user.id}:`, hashErr);
                errorCount++;
            }
        }

        console.log('\nMigration Complete!');
        console.log(`Successfully migrated: ${migratedCount}`);
        console.log(`Errors: ${errorCount}`);
        db.close();
    } catch (err) {
        console.error('Migration error:', err);
        db.close();
    }
}

migratePasswords();
