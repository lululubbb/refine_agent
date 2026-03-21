package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_6_5Test {

    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    void setUp() {
        values = new String[] { "val0", "val1", "val2" };
        mapping = new HashMap<>();
        mapping.put("key0", 0);
        mapping.put("key1", 1);
        mapping.put("key2", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1L);
    }

    @Test
    @Timeout(8000)
    void testIsSet_whenMappedAndIndexInBounds_returnsTrue() {
        assertTrue(csvRecord.isSet("key0"));
        assertTrue(csvRecord.isSet("key1"));
        assertTrue(csvRecord.isSet("key2"));
    }

    @Test
    @Timeout(8000)
    void testIsSet_whenMappedButIndexOutOfBounds_returnsFalse() {
        Map<String, Integer> mappingOut = new HashMap<>(mapping);
        mappingOut.put("keyOut", 5);
        CSVRecord record = new CSVRecord(values, mappingOut, null, 1L);
        assertFalse(record.isSet("keyOut"));
    }

    @Test
    @Timeout(8000)
    void testIsSet_whenNotMapped_returnsFalse() {
        assertFalse(csvRecord.isSet("notMapped"));
        assertFalse(csvRecord.isSet(null));
    }

    @Test
    @Timeout(8000)
    void testIsSet_privateMethodInvocation_reflection() throws Exception {
        Method isSetMethod = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        isSetMethod.setAccessible(true);

        assertTrue((boolean) isSetMethod.invoke(csvRecord, "key1"));
        assertFalse((boolean) isSetMethod.invoke(csvRecord, "notMapped"));

        Map<String, Integer> mappingOut = new HashMap<>(mapping);
        mappingOut.put("keyOut", 10);
        CSVRecord record = new CSVRecord(values, mappingOut, null, 1L);
        assertFalse((boolean) isSetMethod.invoke(record, "keyOut"));
    }
}