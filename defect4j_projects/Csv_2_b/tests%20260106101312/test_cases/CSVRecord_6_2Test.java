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

public class CSVRecord_6_2Test {

    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
        values = new String[] {"val0", "val1", "val2"};
    }

    @Test
    @Timeout(8000)
    public void testIsSet_NameMappedAndIndexInRange() {
        mapping.put("key1", 1);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        boolean result = csvRecord.isSet("key1");
        assertTrue(result);
    }

    @Test
    @Timeout(8000)
    public void testIsSet_NameMappedButIndexOutOfRange() {
        mapping.put("key1", 5);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        boolean result = csvRecord.isSet("key1");
        assertFalse(result);
    }

    @Test
    @Timeout(8000)
    public void testIsSet_NameNotMapped() {
        mapping.put("key1", 1);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        boolean result = csvRecord.isSet("unknown");
        assertFalse(result);
    }

    @Test
    @Timeout(8000)
    public void testIsSet_UsingReflection() throws Exception {
        mapping.put("key1", 2);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        Method isSetMethod = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        isSetMethod.setAccessible(true);

        boolean result = (boolean) isSetMethod.invoke(csvRecord, "key1");
        assertTrue(result);

        result = (boolean) isSetMethod.invoke(csvRecord, "unknown");
        assertFalse(result);
    }
}