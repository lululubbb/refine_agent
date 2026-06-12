package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_4Test {

    @Test
    public void testisSet_nameMappedAndWithinBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        boolean result = invokeIsSet(record, "key1");
        Assertions.assertEquals(true, result, "Expected 'key1' to be set and within bounds.");
    }

    @Test
    public void testisSet_nameMappedButOutOfBounds() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 1);
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        boolean result = invokeIsSet(record, "key1");
        Assertions.assertEquals(false, result, "Expected 'key1' to be out of bounds.");
    }

    @Test
    public void testisSet_nameNotMapped() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        boolean result = invokeIsSet(record, "key1");
        Assertions.assertEquals(false, result, "Expected 'key1' to not be mapped.");
    }

    @Test
    public void testisSet_emptyValuesArray() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        String[] values = {};
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        boolean result = invokeIsSet(record, "key1");
        Assertions.assertEquals(false, result, "Expected 'key1' to be out of bounds due to empty values.");
    }

    private boolean invokeIsSet(CSVRecord record, String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(record, name);
    }
}