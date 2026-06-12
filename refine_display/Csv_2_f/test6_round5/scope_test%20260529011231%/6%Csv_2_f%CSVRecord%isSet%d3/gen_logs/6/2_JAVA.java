package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_6_6Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() {
        String[] values = {"value1", "value2", "value3"};
        mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        csvRecord = new CSVRecord(values, mapping, null, 1);
    }

    @Test
    void testisSet_keyExistsAndWithinBounds() throws Exception {
        assertTrue(csvRecord.isSet("key1"));
    }

    @Test
    void testisSet_keyExistsButOutOfBounds() throws Exception {
        mapping.put("key3", 3);
        assertFalse(csvRecord.isSet("key3"));
    }

    @Test
    void testisSet_keyDoesNotExist() throws Exception {
        assertFalse(csvRecord.isSet("keyNonExistent"));
    }

    @Test
    void testisSet_keyExistsButNotMapped() throws Exception {
        mapping.clear();
        assertFalse(csvRecord.isSet("key1"));
    }

    @Test
    void testisSet_emptyMapping() throws Exception {
        mapping.clear();
        assertFalse(csvRecord.isSet("key1"));
    }

    @Test
    void testisSet_nullKey() throws Exception {
        assertThrows(NullPointerException.class, () -> csvRecord.isSet(null));
    }
}