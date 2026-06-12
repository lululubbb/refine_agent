package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_2Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        mapping.put("key3", 3); // This key is out of bounds
        csvRecord = new CSVRecord(values, mapping, "comment", 1L);
    }

    @Test
    public void testisSet_keyExistsAndWithinBounds() throws Exception {
        boolean result = invokeIsSet("key1");
        Assertions.assertEquals(true, result);
    }

    @Test
    public void testisSet_keyExistsAndOutOfBounds() throws Exception {
        boolean result = invokeIsSet("key3");
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_keyDoesNotExist() throws Exception {
        boolean result = invokeIsSet("key4");
        Assertions.assertEquals(false, result);
    }

    @Test
    public void testisSet_emptyMapping() throws Exception {
        mapping.clear();
        boolean result = invokeIsSet("key1");
        Assertions.assertEquals(false, result);
    }

    private boolean invokeIsSet(String name) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("isSet", String.class);
        method.setAccessible(true);
        return (boolean) method.invoke(csvRecord, name);
    }
}