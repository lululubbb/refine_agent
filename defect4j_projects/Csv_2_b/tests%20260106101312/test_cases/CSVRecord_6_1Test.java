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

class CSVRecord_6_1Test {

    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    void setUp() {
        values = new String[] {"val0", "val1", "val2"};
        mapping = new HashMap<>();
        mapping.put("key0", 0);
        mapping.put("key1", 1);
        mapping.put("key2", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1L);
    }

    @Test
    @Timeout(8000)
    void testIsSet_nameMappedAndIndexInBounds() throws Exception {
        Method isSetMethod = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        isSetMethod.setAccessible(true);
        boolean result = (boolean) isSetMethod.invoke(csvRecord, "key1");
        assertTrue(result);
    }

    @Test
    @Timeout(8000)
    void testIsSet_nameMappedButIndexOutOfBounds() throws Exception {
        mapping.put("keyOutOfBounds", values.length);
        CSVRecord record = new CSVRecord(values, mapping, null, 1L);

        Method isSetMethod = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        isSetMethod.setAccessible(true);
        boolean result = (boolean) isSetMethod.invoke(record, "keyOutOfBounds");
        assertFalse(result);
    }

    @Test
    @Timeout(8000)
    void testIsSet_nameNotMapped() throws Exception {
        Method isSetMethod = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        isSetMethod.setAccessible(true);
        boolean result = (boolean) isSetMethod.invoke(csvRecord, "nonExistingKey");
        assertFalse(result);
    }

    @Test
    @Timeout(8000)
    void testIsSet_nullName() throws Exception {
        Method isSetMethod = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        isSetMethod.setAccessible(true);
        boolean result = (boolean) isSetMethod.invoke(csvRecord, new Object[] {null});
        assertFalse(result);
    }
}