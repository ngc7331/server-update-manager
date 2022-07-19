import { ENDPOINT, PROJECT_ID, DATABASE_ID, COLLECTION_ID } from './conf.js'

function isNull(v) {
    if (v===null || v === 'null') return true;
    else return false;
}

function stringify(v) {
    var res = [];
    for (var i=0; i<v.length; i++) {
        res.push(JSON.stringify(v[i]));
    }
    return res;
}

Vue.createApp({
    data() {
        return {
            email: '',
            password: '',
            loggedin: false,
            session_id: null,
            save_session: true,
            documents: {},
            unsubscribe: null,
            proc_msg: ["update", "hold", "upgrade", "autoremove"]
        }
    },
    mounted() {
        var app = this;
        const client = new Appwrite.Client();
        client.setEndpoint(ENDPOINT).setProject(PROJECT_ID);
        app.client = client;

        const account = new Appwrite.Account(client);
        app.account = account;

        const db = new Appwrite.Databases(client, DATABASE_ID);
        app.db = db;

        if (isNull(localStorage.getItem('appwrite_save_session'))) app.save_session = true;
        else app.save_session = localStorage.getItem('appwrite_save_session');
        app.session_id = localStorage.getItem('appwrite_session_id');

        app.getSession();

        app.refreshDocuments();
    },
    watch: {
        loggedin() {
            if (this.loggedin) {
                Swal.fire('Success', 'logged in, session_id='+this.session_id, 'success');
            }
            else Swal.fire('Success', 'logged out', 'success');
        },
        session_id() {
            if (this.save_session) this.saveSession();
        },
        save_session() {
            localStorage.setItem('appwrite_save_session', this.save_session);
            if (!this.save_session) {
                localStorage.removeItem('appwrite_session_id');
            }
        }
    },
    methods: {
        createSession() {
            var app = this;
            let promise = app.account.createEmailSession(app.email, app.password);
            promise.then(function (response) {
                app.session_id = response.$id;
                app.loggedin = true;
            }, function (error) {
                Swal.fire('Login failed', error.message, 'error');
                console.log(error); // Failure
            });
        },
        deleteSession() {
            var app = this;
            if (!app.loggedin) return ;
            app.documents = {};

            if (app.unsubscribe != null)
                app.unsubscribe();
            app.unsubscribe = null;

            let promise = app.account.deleteSession(app.session_id);
            promise.then(function (response) {
                app.session_id = null;
                app.loggedin = false;
            }, function (error) {
                Swal.fire('Unknown Appwrite Error', error.message, 'error');
                console.log(error); // Failure
            });
        },
        saveSession() {
            if (!isNull(this.session_id)) localStorage.setItem('appwrite_session_id', this.session_id);
            else localStorage.removeItem('appwrite_session_id')
        },
        getSession() {
            var app = this;
            if (!isNull(app.session_id)) {
                console.log('Trying to log in with saved session_id');
                let promise = app.account.getSession(app.session_id);
                promise.then(function (response) {
                    app.loggedin = true;
                }, function (error) {
                    console.log(error); // Failure
                    Swal.fire('Login failed', error.message, 'error');
                    app.session_id = null;
                    app.loggedin = false;
                });
            }
            else {
                console.log('Not trying to log in session since session_id is null');
            }
        },
        parseDocument(doc) {
            var progs = [];
            for (var j=0; j<doc.progs.length; j++) {
                var prog = JSON.parse(doc.progs[j])
                progs.push({
                    "name": prog.name,
                    "hold": prog.hold,
                    "version": prog.version
                });
            }
            return {
                "id": doc.$id,
                "name": doc.name,
                "time": doc.time,
                "status": doc.status,
                "progs": progs,
                "msg": doc.msg,
                "log": doc.log,
                "error": doc.error
            }
        },
        refreshDocuments() {
            var app = this;

            if (app.unsubscribe != null)
                app.unsubscribe();

            app.documents = {};
            let promise = app.db.listDocuments(COLLECTION_ID);
            promise.then(function (response) {
                console.log(response);
                for (var i=0; i<response.total; i++) {
                    var doc = response.documents[i];
                    app.documents[doc.$id] = app.parseDocument(doc);
                }
            }, function (error) {
                Swal.fire('Unknown Appwrite Error', error.message, 'error');
                console.log(error); // Failure
            });

            app.unsubscribe = app.client.subscribe(`databases.${DATABASE_ID}.collections.${COLLECTION_ID}.documents`, response => {
                console.log(response);
                if (response.events[1] === 'databases.*.collections.*.documents.*.delete')
                    delete app.documents[response.payload.$id];
                else
                    app.documents[response.payload.$id] = app.parseDocument(response.payload);
            })
        },
        saveDocument() {
            var app = this;
            var error_occured = false;
            for(var key in app.documents) {
                var doc = app.documents[key];
                var document = {
                    "status": doc.status,
                    "progs": stringify(doc.progs)
                };
                let promise = app.db.updateDocument(COLLECTION_ID, key, document);
                promise.then(function (response) {
                    console.log(response); // Success
                }, function (error) {
                    error_occured = true;
                    Swal.fire('Unknown Appwrite Error', error.message, 'error');
                    console.log(error); // Failure
                });
            }
            if (!error_occured) Swal.fire('Success', 'Document saved to appwrite', 'success');
        }
    }
}).mount('#app');
